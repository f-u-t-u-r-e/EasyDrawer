"""LangGraph 工作流 v0.3 — 核心 Agent 编排

流程（8 节点）：
  optimize_prompt → optimize_parameters → generate_images → score_images
  → evaluate_quality ──(accept)──→ seed_refine → img2img_refine → build_response
                     └─(refine)──→ optimize_prompt（反馈循环）

v0.3 新增节点：
- optimize_prompt: 生成 3 个提示词变体（Ensemble）
- generate_images: 每个变体生成 1 张，共 3 张（多样性 ↑，并发执行）
- seed_refine: 固定 seed，微调 CFG/guidance 搜索更好的变体
- img2img_refine: 对最佳图片做低降噪精修
"""

import asyncio
import logging
import math
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
    LLMConfig,
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
    llm_config: LLMConfig | None  # 每请求独立的 LLM 配置（线程安全）

    # 中间状态
    optimized_prompt: OptimizedPrompt | None
    parameters: list[dict] | None  # 多变体参数列表
    generated_images: list[GeneratedImage] | None
    scores: list[dict] | None
    refinement_round: int
    refinement_feedback: str | None
    param_adjustment: dict | None  # 反馈循环的参数调整建议 (优化3)

    # 输出
    response: GenerationResponse | None
    error: str | None

    # 元信息
    start_time: float
    messages: Annotated[list, add_messages]
    events: list[dict]  # SSE 事件队列


class ImageGenerationAgent:
    """图片生成 Agent — LangGraph 工作流"""

    def __init__(self, history_service=None) -> None:
        self.prompt_optimizer = PromptOptimizer()
        self.param_optimizer = ParameterOptimizer()
        self.sd_client = StableDiffusionClient()
        self.flux_client = FLUXClient()
        self.quality_scorer = QualityScorer()
        self.history_service = history_service  # bandit 反馈用

        # 并发控制信号量 — 限制同时执行的生图任务数
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_generations)

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

        # 错误边：optimize_prompt 失败 → END（由 generate() 抛异常）
        workflow.add_conditional_edges(
            "optimize_prompt",
            self._has_error,
            {"error": END, "continue": "optimize_parameters"},
        )

        workflow.add_edge("optimize_parameters", "generate_images")

        # 错误边：generate_images 失败 → END
        workflow.add_conditional_edges(
            "generate_images",
            self._has_error,
            {"error": END, "continue": "score_images"},
        )

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

    def _has_error(self, state: AgentState) -> str:
        """条件分支：检查节点是否产生了错误"""
        if state.get("error"):
            return "error"
        return "continue"

    # ── 节点实现 ─────────────────────────────────────────────

    async def _optimize_prompt(self, state: AgentState) -> dict:
        """步骤 1: 优化提示词 — 生成 3 个变体"""
        request = state["request"]
        feedback = state.get("refinement_feedback")
        round_num = state.get("refinement_round", 0)
        llm_config = state.get("llm_config")

        prefix = f"[轮次{round_num + 1}] " if round_num > 0 else ""

        # 线程安全：每请求独立的 optimizer，不修改全局 agent
        if llm_config and llm_config.api_key:
            optimizer = PromptOptimizer(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model=llm_config.model,
            )
        else:
            optimizer = self.prompt_optimizer

        try:
            optimized = await optimizer.optimize(
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
        """步骤 2: 为每个变体生成独立参数

        优化2: 从 history 读取历史参数统计，传给 ParameterOptimizer 做 bandit 调整
        优化3: 读取 param_adjustment（反馈循环的参数调整建议）
        """
        request = state["request"]
        optimized_prompt = state["optimized_prompt"]
        backend = state["backend"]
        param_adjustment = state.get("param_adjustment")

        variants = optimized_prompt.variants
        if not variants:
            # 回退：只有主提示词
            variants = [type("V", (), {"enhanced": optimized_prompt.enhanced, "negative": optimized_prompt.negative})()]

        # 从历史数据库读取参数统计（bandit 反馈）
        history_stats = None
        if self.history_service:
            try:
                scene_str = optimized_prompt.scene_type.value if optimized_prompt.scene_type else "artistic"
                style_str = optimized_prompt.style.value if optimized_prompt.style else None
                history_stats = await self.history_service.get_parameter_stats_async(
                    scene_type=scene_str,
                    style=style_str,
                    backend=backend,
                    limit=50,
                )
            except Exception as e:
                logger.warning("读取历史参数统计失败（非致命）: %s", e)

        param_list = []
        for idx, variant in enumerate(variants):
            if backend == "flux":
                params = self.param_optimizer.optimize_flux(
                    prompt=variant.enhanced,
                    scene_type=optimized_prompt.scene_type,
                    width=request.width,
                    height=request.height,
                    history=history_stats,
                    param_adjustment=param_adjustment if idx == 0 else None,
                ).model_dump()
            else:
                params = self.param_optimizer.optimize_sd(
                    prompt=variant.enhanced,
                    negative_prompt=variant.negative,
                    scene_type=optimized_prompt.scene_type,
                    style=optimized_prompt.style,
                    width=request.width,
                    height=request.height,
                    history=history_stats,
                    param_adjustment=param_adjustment if idx == 0 else None,
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
        """步骤 3: Ensemble 生成 — 每个变体并发生成 1 张，共 N 张"""
        backend = state["backend"]
        param_list = state["parameters"]

        async def _generate_single_variant(
            variant_idx: int, params_dict: dict
        ) -> list[GeneratedImage]:
            """生成单个变体（并发任务）"""
            if backend == "flux":
                params = FLUXParameters(**params_dict)
                images = await self.flux_client.generate(params, batch_size=1)
            else:
                params = SDParameters(**params_dict)
                images = await self.sd_client.generate(params, batch_size=1)
            for img in images:
                img.variant_index = variant_idx
            return images

        try:
            # 并发生成所有变体 — 比串行快约 60%
            tasks = [
                _generate_single_variant(idx, params_dict)
                for idx, params_dict in enumerate(param_list)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_images: list[GeneratedImage] = []
            for r in results:
                if isinstance(r, list):
                    all_images.extend(r)
                elif isinstance(r, Exception):
                    logger.warning("单个变体生成失败（跳过）: %s", r)

            if not all_images:
                raise RuntimeError("所有变体生成均失败")

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
        """步骤 5: 评估是否需要反馈循环

        优化3: 不仅调整提示词，还根据薄弱维度生成参数调整建议
        """
        scores = state["scores"]
        best_score = max(s["overall"] for s in scores)
        round_num = state.get("refinement_round", 0)

        if best_score < settings.quality_threshold and round_num < settings.max_refinement_rounds:
            # 基于最佳图片的薄弱维度构建反馈（而非最差图片）
            best = max(scores, key=lambda s: s["overall"])

            # 提示词反馈
            feedback_parts = []
            if best["clip_similarity"] < 60:
                feedback_parts.append("提示词与图片匹配度低，请更精确地描述主体")
            if best["aesthetic_score"] < 60:
                feedback_parts.append("美学评分低，请增强光影和构图描述")
            if best["sharpness"] < 60:
                feedback_parts.append("图片不够清晰，请添加 sharp focus 等质量词")

            feedback = (
                "；".join(feedback_parts)
                if feedback_parts
                else f"整体质量偏低（最高分 {best_score:.1f}），请增强细节描述"
            )

            # 参数调整建议（优化3: 联合调参）
            # 根据薄弱维度调整生图参数，而非仅调提示词
            param_adjustment = {}
            if state["backend"] == "flux":
                # FLUX: 调 guidance（类似 SD 的 CFG）
                if best["clip_similarity"] < 60:
                    param_adjustment["guidance_delta"] = +0.5  # 提高 prompt 遵循度
                if best["sharpness"] < 60:
                    param_adjustment["guidance_delta"] = param_adjustment.get("guidance_delta", 0) + 0.3
            else:
                # SD: 调 CFG + Steps
                if best["clip_similarity"] < 60:
                    param_adjustment["cfg_delta"] = +0.5  # 提高 prompt 遵循度
                if best["sharpness"] < 60:
                    param_adjustment["steps_delta"] = +3  # 更多步数 → 更清晰
                    param_adjustment["cfg_delta"] = param_adjustment.get("cfg_delta", 0) + 0.3

            return {
                "refinement_round": round_num + 1,
                "refinement_feedback": feedback,
                "param_adjustment": param_adjustment if param_adjustment else None,
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
            "refinement_feedback": None,
            "param_adjustment": None,  # 清除调整建议
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
        """步骤 6: 变体搜索 — 固定最佳 seed，微调 CFG/guidance 搜索更好的变体"""
        images = state["generated_images"]
        optimized_prompt = state["optimized_prompt"]
        backend = state["backend"]

        # 找到当前最佳
        best_img = max(images, key=lambda i: i.quality_score or 0)

        try:
            if backend == "flux":
                # FLUX: 固定 seed，微调 guidance
                flux_params = FLUXParameters(**state["parameters"][best_img.variant_index])
                flux_params = flux_params.model_copy(update={"seed": best_img.seed})
                variant_images = await self.flux_client.generate_variants(
                    flux_params, guidance_offsets=[-0.5, 0.5, 1.0]
                )
            else:
                # SD: 固定 seed，微调 CFG
                sd_params = SDParameters(**state["parameters"][best_img.variant_index])
                sd_params = sd_params.model_copy(update={"seed": best_img.seed})
                variant_images = await self.sd_client.generate_variants(
                    sd_params, cfg_offsets=[-0.5, 0.5, 1.0]
                )

            if variant_images:
                # 评分变体图片
                variant_data = [img.image_data for img in variant_images]
                variant_prompt = optimized_prompt.variants[best_img.variant_index].enhanced \
                    if optimized_prompt.variants and best_img.variant_index < len(optimized_prompt.variants) \
                    else optimized_prompt.enhanced
                variant_scores = await self.quality_scorer.score_batch(
                    variant_data, variant_prompt
                )

                for img, scores in zip(variant_images, variant_scores):
                    img.quality_score = scores["overall"]
                    img.quality_breakdown = QualityBreakdown(**scores)
                    img.variant_index = best_img.variant_index

                # 合并到总列表
                images = list(images) + variant_images

                new_best = max(images, key=lambda i: i.quality_score or 0)
                improvement = (new_best.quality_score or 0) - (best_img.quality_score or 0)
                message = f"变体搜索完成: +{len(variant_images)} 张"
                if improvement > 0:
                    message += f"，分数提升 +{improvement:.1f}"
            else:
                message = "变体搜索完成: 无额外变体"

        except Exception as e:
            logger.warning("变体搜索失败（非致命）: %s", e)
            message = f"变体搜索跳过: {e}"

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

            # 评分精修后的图片（用异步方法避免阻塞事件循环）
            prompt_text = optimized_prompt.variants[variant_idx].enhanced \
                if optimized_prompt.variants and variant_idx < len(optimized_prompt.variants) \
                else optimized_prompt.enhanced
            scores = await self.quality_scorer.score_batch(
                [refined_img.image_data], prompt_text
            )
            score = scores[0]
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
        """步骤 8: 构建最终响应 — 使用 MMR 多样性选图"""
        images = state["generated_images"]

        # MMR 多样性选图：α * quality + (1-α) * diversity
        best_image = await self._select_best_mmr(images)

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

    async def _select_best_mmr(
        self, images: list[GeneratedImage], alpha: float = 0.7
    ) -> GeneratedImage:
        """MMR (Maximal Marginal Relevance) 选图

        在质量分接近时，倾向选择与已选图片差异最大的候选，
        保留 Ensemble 多样性价值。

        MMR(i) = α * quality(i) + (1-α) * max_dist(i, all_others)

        Args:
            images: 候选图片列表
            alpha: 质量权重 (0-1)，默认 0.7
        """
        if len(images) <= 1:
            return images[0] if images else None

        # 按质量分排序
        scored = sorted(images, key=lambda i: i.quality_score or 0, reverse=True)

        # 如果最高分与次高分差距 > 5 分，直接选最高分（质量碾压）
        if (scored[0].quality_score or 0) - (scored[1].quality_score or 0) > 5.0:
            return scored[0]

        # 分数接近 → 用 MMR 选图
        # 计算 CLIP embedding 用于多样性度量
        image_data_list = [img.image_data for img in scored]
        embeddings = await self.quality_scorer.compute_image_embeddings(image_data_list)

        if not embeddings or len(embeddings) != len(scored):
            # 无 embedding → 回退到纯最高分
            return scored[0]

        # 对每张图片计算 MMR = α * quality + (1-α) * max_distance_to_others
        best_mmr = -1.0
        best_idx = 0
        for i in range(len(scored)):
            quality = scored[i].quality_score or 0
            # 归一化 quality 到 0-1
            scores_list = [s.quality_score or 0 for s in scored]
            min_q, max_q = min(scores_list), max(scores_list)
            norm_quality = (quality - min_q) / (max_q - min_q + 1e-8)

            # 计算与所有其他图片的最大余弦距离
            max_dist = 0.0
            for j in range(len(scored)):
                if i == j:
                    continue
                # 余弦相似度（embedding 已归一化）
                sim = sum(a * b for a, b in zip(embeddings[i], embeddings[j]))
                dist = 1.0 - sim
                if dist > max_dist:
                    max_dist = dist

            mmr = alpha * norm_quality + (1 - alpha) * max_dist
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i

        return scored[best_idx]

    # ── 执行接口 ─────────────────────────────────────────────

    async def generate(
        self, request: GenerationRequest, llm_config: LLMConfig | None = None
    ) -> GenerationResponse:
        """同步执行完整生成流程

        Args:
            request: 生成请求
            llm_config: 每请求独立的 LLM 配置（线程安全，不修改全局 agent）
        """
        async with self._semaphore:
            session_id = request.session_id or str(uuid.uuid4())
            backend = request.backend.value if request.backend else settings.image_backend

            initial_state: AgentState = {
                "request": request,
                "session_id": session_id,
                "backend": backend,
                "llm_config": llm_config,
                "optimized_prompt": None,
                "parameters": None,
                "generated_images": None,
                "scores": None,
                "refinement_round": 0,
                "refinement_feedback": None,
                "param_adjustment": None,
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

    async def generate_stream(
        self, request: GenerationRequest, llm_config: LLMConfig | None = None
    ):
        """流式执行，逐步 yield SSE 事件

        Args:
            request: 生成请求
            llm_config: 每请求独立的 LLM 配置（线程安全）
        """
        async with self._semaphore:
            session_id = request.session_id or str(uuid.uuid4())
            backend = request.backend.value if request.backend else settings.image_backend

            initial_state: AgentState = {
                "request": request,
                "session_id": session_id,
                "backend": backend,
                "llm_config": llm_config,
                "optimized_prompt": None,
                "parameters": None,
                "generated_images": None,
                "scores": None,
                "refinement_round": 0,
                "refinement_feedback": None,
                "param_adjustment": None,
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
