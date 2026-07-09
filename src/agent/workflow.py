"""LangGraph 工作流 v0.3 — 核心 Agent 编排

流程（8 节点）：
  optimize_prompt → optimize_parameters → generate_images → score_images
  → evaluate_quality ──(accept)──→ seed_refine → img2img_refine → build_response
                     └─(refine)──→ optimize_prompt（反馈循环）

v0.3 新增节点：
- optimize_prompt: 生成 3 个提示词变体（Ensemble）
- generate_images: 每个变体生成 1 张，共 3 张（多样性 ↑）
- seed_refine: 在最佳 seed ± 范围内搜索更好的变体
- img2img_refine: 对最佳图片做低降噪精修
"""

import logging
import time
import uuid
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.models.schemas import (
    GenerationRequest,
    GenerationResponse,
    GeneratedImage,
    OptimizedPrompt,
    QualityBreakdown,
    SDParameters,
    FLUXParameters,
    StreamEvent,
)
from src.services.prompt_optimizer import PromptOptimizer
from src.services.parameter_optimizer import ParameterOptimizer
from src.services.sd_client import StableDiffusionClient
from src.services.flux_client import FLUXClient
from src.services.quality_scorer import QualityScorer

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Agent 状态定义"""

    # 输入
    request: GenerationRequest
    session_id: str
    backend: str  # "sd" | "flux"

    # 中间状态
    optimized_prompt: OptimizedPrompt | None
    parameters: list[dict] | None  # 多变体参数列表
    generated_images: list[GeneratedImage] | None
    scores: list[dict] | None
    refinement_round: int
    refinement_feedback: str | None

    # 输出
    response: GenerationResponse | None
    error: str | None

    # 元信息
    start_time: float
    messages: Annotated[list, add_messages]
    events: list[dict]  # SSE 事件队列


class ImageGenerationAgent:
    """图片生成 Agent — LangGraph 工作流"""

    def __init__(self) -> None:
        self.prompt_optimizer = PromptOptimizer()
        self.param_optimizer = ParameterOptimizer()
        self.sd_client = StableDiffusionClient()
        self.flux_client = FLUXClient()
        self.quality_scorer = QualityScorer()

        self.graph = self._build_graph()

    def _build_graph(self):
        """构建 8 节点状态机"""
        workflow = StateGraph(AgentState)

        workflow.add_node("optimize_prompt", self._optimize_prompt)
        workflow.add_node("optimize_parameters", self._optimize_parameters)
        workflow.add_node("generate_images", self._generate_images)
        workflow.add_node("score_images", self._score_images)
        workflow.add_node("evaluate_quality", self._evaluate_quality)
        workflow.add_node("seed_refine", self._seed_refine)
        workflow.add_node("img2img_refine", self._img2img_refine)
        workflow.add_node("build_response", self._build_response)

        # 主流程
        workflow.add_edge(START, "optimize_prompt")
        workflow.add_edge("optimize_prompt", "optimize_parameters")
        workflow.add_edge("optimize_parameters", "generate_images")
        workflow.add_edge("generate_images", "score_images")
        workflow.add_edge("score_images", "evaluate_quality")

        # 条件分支：质量够 → seed 精搜 → img2img 精修 → 完成
        #           质量不够 → 反馈循环回 optimize_prompt
        workflow.add_conditional_edges(
            "evaluate_quality",
            self._should_refine,
            {"accept": "seed_refine", "refine": "optimize_prompt"},
        )
        workflow.add_edge("seed_refine", "img2img_refine")
        workflow.add_edge("img2img_refine", "build_response")
        workflow.add_edge("build_response", END)

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    # ── 节点实现 ─────────────────────────────────────────────

    async def _optimize_prompt(self, state: AgentState) -> dict:
        """步骤 1: 优化提示词 — 生成 3 个变体"""
        request = state["request"]
        feedback = state.get("refinement_feedback")
        round_num = state.get("refinement_round", 0)

        prefix = f"[轮次{round_num + 1}] " if round_num > 0 else ""

        try:
            optimized = await self.prompt_optimizer.optimize(
                user_prompt=request.prompt,
                style_hint=request.style,
                user_negative=request.negative_prompt,
                feedback=feedback,
            )
        except Exception as e:
            logger.exception("提示词优化失败")
            return {
                "error": f"提示词优化失败: {e}",
                "events": [
                    StreamEvent(
                        step="optimize_prompt",
                        status="error",
                        message=f"提示词优化失败: {e}",
                    ).model_dump()
                ],
            }

        variant_count = len(optimized.variants) if optimized.variants else 1
        return {
            "optimized_prompt": optimized,
            "events": [
                StreamEvent(
                    step="optimize_prompt",
                    status="done",
                    message=f"{prefix}提示词优化完成: {optimized.reasoning} ({variant_count}个变体)",
                    progress=0.15,
                ).model_dump()
            ],
            "messages": [f"✓ {prefix}提示词优化完成 ({variant_count} 变体)"],
        }

    async def _optimize_parameters(self, state: AgentState) -> dict:
        """步骤 2: 为每个变体生成独立参数"""
        request = state["request"]
        optimized_prompt = state["optimized_prompt"]
        backend = state["backend"]

        variants = optimized_prompt.variants
        if not variants:
            # 回退：只有主提示词
            variants = [type("V", (), {"enhanced": optimized_prompt.enhanced, "negative": optimized_prompt.negative})()]

        param_list = []
        for variant in variants:
            if backend == "flux":
                params = self.param_optimizer.optimize_flux(
                    prompt=variant.enhanced,
                    scene_type=optimized_prompt.scene_type,
                    width=request.width,
                    height=request.height,
                ).model_dump()
            else:
                params = self.param_optimizer.optimize_sd(
                    prompt=variant.enhanced,
                    negative_prompt=variant.negative,
                    scene_type=optimized_prompt.scene_type,
                    style=optimized_prompt.style,
                    width=request.width,
                    height=request.height,
                ).model_dump()
            param_list.append(params)

        reasoning = self.param_optimizer.get_reasoning(
            optimized_prompt.scene_type, optimized_prompt.style, backend
        )

        return {
            "parameters": param_list,
            "events": [
                StreamEvent(
                    step="optimize_parameters",
                    status="done",
                    message=f"参数优化完成: {reasoning}",
                    progress=0.25,
                ).model_dump()
            ],
            "messages": [f"✓ 参数优化完成: {reasoning}"],
        }

    async def _generate_images(self, state: AgentState) -> dict:
        """步骤 3: Ensemble 生成 — 每个变体生成 1 张，共 N 张"""
        backend = state["backend"]
        param_list = state["parameters"]

        all_images: list[GeneratedImage] = []

        try:
            for variant_idx, params_dict in enumerate(param_list):
                if backend == "flux":
                    params = FLUXParameters(**params_dict)
                    images = await self.flux_client.generate(params, batch_size=1)
                else:
                    params = SDParameters(**params_dict)
                    images = await self.sd_client.generate(params, batch_size=1)

                for img in images:
                    img.variant_index = variant_idx
                all_images.extend(images)

        except Exception as e:
            logger.exception("图片生成失败")
            return {
                "error": f"图片生成失败: {e}",
                "events": [
                    StreamEvent(
                        step="generate_images",
                        status="error",
                        message=f"图片生成失败: {e}",
                    ).model_dump()
                ],
            }

        return {
            "generated_images": all_images,
            "events": [
                StreamEvent(
                    step="generate_images",
                    status="done",
                    message=f"Ensemble 生成完成: {len(all_images)} 张候选图片",
                    progress=0.5,
                ).model_dump()
            ],
            "messages": [f"✓ 生成完成: {len(all_images)} 张"],
        }

    async def _score_images(self, state: AgentState) -> dict:
        """步骤 4: 批量评分 — 每张图片用自己对应变体的 prompt"""
        images = state["generated_images"]
        optimized_prompt = state["optimized_prompt"]
        variants = optimized_prompt.variants

        # 为每张图片匹配对应的 prompt
        image_data_list = []
        prompt_list = []
        for img in images:
            image_data_list.append(img.image_data)
            if variants and img.variant_index < len(variants):
                prompt_list.append(variants[img.variant_index].enhanced)
            else:
                prompt_list.append(optimized_prompt.enhanced)

        # 批量推理（一次 forward pass）
        score_dicts = await self.quality_scorer.score_batch_per_prompt(
            image_data_list, prompt_list
        )

        for img, scores in zip(images, score_dicts):
            img.quality_score = scores["overall"]
            img.quality_breakdown = QualityBreakdown(**scores)

        best_score = max(s["overall"] for s in score_dicts)

        return {
            "generated_images": images,
            "scores": score_dicts,
            "events": [
                StreamEvent(
                    step="score_images",
                    status="done",
                    message=f"质量评估完成: 最高分 {best_score:.1f}",
                    progress=0.65,
                ).model_dump()
            ],
            "messages": [f"✓ 质量评估完成: 最高分 {best_score:.1f}"],
        }

    async def _evaluate_quality(self, state: AgentState) -> dict:
        """步骤 5: 评估是否需要反馈循环"""
        scores = state["scores"]
        best_score = max(s["overall"] for s in scores)
        round_num = state.get("refinement_round", 0)

        if best_score < settings.quality_threshold and round_num < settings.max_refinement_rounds:
            # 诊断最差维度，构建反馈
            worst = min(scores, key=lambda s: s["overall"])
            feedback_parts = []
            if worst["clip_similarity"] < 60:
                feedback_parts.append("提示词与图片匹配度低，请更精确地描述主体")
            if worst["aesthetic_score"] < 60:
                feedback_parts.append("美学评分低，请增强光影和构图描述")
            if worst["sharpness"] < 60:
                feedback_parts.append("图片不够清晰，请添加 sharp focus 等质量词")

            feedback = (
                "；".join(feedback_parts)
                if feedback_parts
                else "整体质量偏低，请增强细节描述"
            )

            return {
                "refinement_round": round_num + 1,
                "refinement_feedback": feedback,
                "events": [
                    StreamEvent(
                        step="evaluate_quality",
                        status="done",
                        message=f"分数 {best_score:.1f} 低于阈值 {settings.quality_threshold}，"
                                f"进入第 {round_num + 2} 轮优化",
                        progress=0.4,
                    ).model_dump()
                ],
            }

        return {
            "refinement_round": round_num,
            "refinement_feedback": None,  # 清除 feedback 标记
            "events": [
                StreamEvent(
                    step="evaluate_quality",
                    status="done",
                    message=f"质量合格 ({best_score:.1f})，进入精搜阶段",
                    progress=0.7,
                ).model_dump()
            ],
        }

    def _should_refine(self, state: AgentState) -> str:
        """条件分支：决定是否反馈循环"""
        feedback = state.get("refinement_feedback")
        if feedback:
            return "refine"
        return "accept"

    async def _seed_refine(self, state: AgentState) -> dict:
        """步骤 6: Seed 邻域搜索 — 在最佳 seed ± 范围内搜索更好的构图"""
        images = state["generated_images"]
        optimized_prompt = state["optimized_prompt"]
        backend = state["backend"]

        # 找到当前最佳
        best_img = max(images, key=lambda i: i.quality_score or 0)
        best_seed = best_img.seed

        try:
            if backend == "flux":
                # FLUX seed 邻域
                flux_params = FLUXParameters(**state["parameters"][best_img.variant_index])
                neighbor_images = await self.flux_client.generate_seed_neighbors(
                    flux_params, best_seed, offsets=[-1, 1, 2]
                )
            else:
                # SD seed 邻域
                sd_params = SDParameters(**state["parameters"][best_img.variant_index])
                neighbor_images = await self.sd_client.generate_seed_neighbors(
                    sd_params, best_seed, offsets=[-1, 1, 2]
                )

            if neighbor_images:
                # 评分邻域图片
                neighbor_data = [img.image_data for img in neighbor_images]
                neighbor_prompt = optimized_prompt.variants[best_img.variant_index].enhanced \
                    if optimized_prompt.variants and best_img.variant_index < len(optimized_prompt.variants) \
                    else optimized_prompt.enhanced
                neighbor_scores = await self.quality_scorer.score_batch(
                    neighbor_data, neighbor_prompt
                )

                for img, scores in zip(neighbor_images, neighbor_scores):
                    img.quality_score = scores["overall"]
                    img.quality_breakdown = QualityBreakdown(**scores)
                    img.variant_index = best_img.variant_index

                # 合并到总列表
                images = list(images) + neighbor_images

                new_best = max(images, key=lambda i: i.quality_score or 0)
                improvement = (new_best.quality_score or 0) - (best_img.quality_score or 0)
                message = f"Seed 精搜完成: +{len(neighbor_images)} 张"
                if improvement > 0:
                    message += f"，分数提升 +{improvement:.1f}"
            else:
                message = "Seed 精搜完成: 无额外变体"

        except Exception as e:
            logger.warning("Seed 精搜失败（非致命）: %s", e)
            message = f"Seed 精搜跳过: {e}"

        return {
            "generated_images": images,
            "events": [
                StreamEvent(
                    step="seed_refine",
                    status="done",
                    message=message,
                    progress=0.8,
                ).model_dump()
            ],
            "messages": [f"✓ {message}"],
        }

    async def _img2img_refine(self, state: AgentState) -> dict:
        """步骤 7: img2img 精修 — 对最佳图片做低降噪二次优化"""
        images = state["generated_images"]
        backend = state["backend"]
        optimized_prompt = state["optimized_prompt"]

        best_img = max(images, key=lambda i: i.quality_score or 0)

        # FLUX 暂不支持 img2img，跳过
        if backend == "flux":
            return {
                "generated_images": images,
                "events": [
                    StreamEvent(
                        step="img2img_refine",
                        status="done",
                        message="FLUX 后端跳过 img2img 精修",
                        progress=0.9,
                    ).model_dump()
                ],
            }

        try:
            # 构建 img2img 参数
            variant_idx = best_img.variant_index
            sd_params = SDParameters(**state["parameters"][variant_idx])
            sd_params = sd_params.model_copy(update={"seed": best_img.seed})

            refined_img = await self.sd_client.img2img_refine(
                params=sd_params,
                init_image_b64=best_img.image_data,
                denoising_strength=0.25,
            )

            # 评分精修后的图片
            prompt_text = optimized_prompt.variants[variant_idx].enhanced \
                if optimized_prompt.variants and variant_idx < len(optimized_prompt.variants) \
                else optimized_prompt.enhanced
            score = self.quality_scorer.score_image(
                refined_img.image_data, prompt_text
            )
            refined_img.quality_score = score["overall"]
            refined_img.quality_breakdown = QualityBreakdown(**score)
            refined_img.variant_index = variant_idx
            refined_img.is_refined = True

            # 只有精修后分数更高才保留
            if (refined_img.quality_score or 0) > (best_img.quality_score or 0):
                images = list(images) + [refined_img]
                improvement = refined_img.quality_score - (best_img.quality_score or 0)
                message = f"img2img 精修成功: 分数 +{improvement:.1f}"
            else:
                message = "img2img 精修完成: 原图更好，保留原图"

        except Exception as e:
            logger.warning("img2img 精修失败（非致命）: %s", e)
            message = f"img2img 精修跳过: {e}"

        return {
            "generated_images": images,
            "events": [
                StreamEvent(
                    step="img2img_refine",
                    status="done",
                    message=message,
                    progress=0.9,
                ).model_dump()
            ],
            "messages": [f"✓ {message}"],
        }

    async def _build_response(self, state: AgentState) -> dict:
        """步骤 8: 构建最终响应"""
        images = state["generated_images"]

        # 选择评分最高的
        best_image = max(images, key=lambda i: i.quality_score or 0)

        generation_time = time.time() - state["start_time"]

        response = GenerationResponse(
            session_id=state["session_id"],
            optimized_prompt=state["optimized_prompt"],
            images=images,
            best_image=best_image,
            generation_time=generation_time,
            refinement_rounds=state.get("refinement_round", 0),
            backend_used=state["backend"],
        )

        return {
            "response": response,
            "events": [
                StreamEvent(
                    step="build_response",
                    status="done",
                    message=f"完成! 总耗时 {generation_time:.1f}s，"
                            f"最终 {len(images)} 张，"
                            f"最高分 {best_image.quality_score:.1f}",
                    progress=1.0,
                ).model_dump()
            ],
            "messages": [f"✓ 完成! 总耗时 {generation_time:.1f}s"],
        }

    # ── 执行接口 ─────────────────────────────────────────────

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """同步执行完整生成流程"""
        session_id = request.session_id or str(uuid.uuid4())
        backend = request.backend.value if request.backend else settings.image_backend

        initial_state: AgentState = {
            "request": request,
            "session_id": session_id,
            "backend": backend,
            "optimized_prompt": None,
            "parameters": None,
            "generated_images": None,
            "scores": None,
            "refinement_round": 0,
            "refinement_feedback": None,
            "response": None,
            "error": None,
            "start_time": time.time(),
            "messages": [],
            "events": [],
        }

        config = {"configurable": {"thread_id": session_id}}
        final_state = await self.graph.ainvoke(initial_state, config)

        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        return final_state["response"]

    async def generate_stream(self, request: GenerationRequest):
        """流式执行，逐步 yield SSE 事件"""
        session_id = request.session_id or str(uuid.uuid4())
        backend = request.backend.value if request.backend else settings.image_backend

        initial_state: AgentState = {
            "request": request,
            "session_id": session_id,
            "backend": backend,
            "optimized_prompt": None,
            "parameters": None,
            "generated_images": None,
            "scores": None,
            "refinement_round": 0,
            "refinement_feedback": None,
            "response": None,
            "error": None,
            "start_time": time.time(),
            "messages": [],
            "events": [],
        }

        config = {"configurable": {"thread_id": session_id}}

        async for event in self.graph.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                events = node_output.get("events", [])
                for e in events:
                    yield e

                if node_output.get("error"):
                    yield StreamEvent(
                        step=node_name,
                        status="error",
                        message=node_output["error"],
                    ).model_dump()
                    return

                if node_output.get("response"):
                    yield {
                        "step": "complete",
                        "status": "done",
                        "message": "生成完成",
                        "progress": 1.0,
                        "data": node_output["response"].model_dump(),
                    }

    async def close(self) -> None:
        """关闭资源"""
        await self.sd_client.close()
        await self.flux_client.close()
