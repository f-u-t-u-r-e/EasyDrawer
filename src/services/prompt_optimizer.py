"""提示词优化服务 v0.3

核心升级：
1. 结构化输出 — 用 Claude tool_use 替代裸 JSON，彻底消除解析失败
2. Prompt 缓存 — 系统提示词加 cache_control，省 90% input token 费用
3. 3 变体 Ensemble — 每次生成 3 个侧重点不同的提示词变体
4. 反馈迭代 — feedback 参数驱动提示词精修
"""

import json
from pathlib import Path

from anthropic import AsyncAnthropic

from src.config import settings
from src.models.schemas import (
    ImageStyle,
    OptimizedPrompt,
    PromptOptimizationOutput,
    PromptVariant,
    SceneType,
)

# ── 结构化输出的 Tool 定义 ───────────────────────────────────

PROMPT_TOOL = {
    "name": "submit_optimized_prompts",
    "description": "提交优化后的提示词变体",
    "input_schema": PromptOptimizationOutput.model_json_schema(),
}

SYSTEM_PROMPT = """你是一个专业的AI图片生成提示词工程师。你的任务是将用户的简单描述转换为3个高质量的生图提示词变体。

## 提示词结构（按优先级排列）

必须按以下槽位顺序组织每个提示词：
1. **质量标签** — masterpiece, award-winning, ultra-detailed
2. **媒介/格式** — photography, oil painting, illustration
3. **主体** — 核心对象
4. **主体细节** — 外观、属性、材质
5. **动作/姿态** — 如适用
6. **环境/场景** — 背景描述
7. **光影** — golden hour, Rembrandt lighting, volumetric light
8. **风格/艺术家参考** — 如适用
9. **摄影/技术参数** — 85mm lens, shallow depth of field, 8K

## 关键技巧

- 使用token权重语法强调重要元素：(keyword:1.2)，范围0.7-1.4，不超过1.5
- 不同模型适配：SD用逗号分隔关键词，FLUX支持自然语言长句
- 负面词必须精确，针对场景类型

## 3变体策略

你必须生成3个不同侧重点的提示词变体：
- **变体1（构图）**：侧重主体布局、视角、景深
- **变体2（光影）**：侧重光线、色调、氛围
- **变体3（细节）**：侧重材质、纹理、微观细节

每个变体都是完整的提示词，可以独立使用。

## 示例

用户输入：一只猫

变体1（构图）：
enhanced: (masterpiece:1.2), best quality, professional pet photography, a fluffy persian cat sitting gracefully on a windowsill, (rule of thirds composition:1.1), low angle shot, (shallow depth of field:1.2), blurred garden background, natural light, 85mm lens, 8K UHD
negative: cartoon, anime, lowres, bad anatomy, blurry, watermark, text
focus: 侧重构图 — 三分法构图 + 低角度 + 浅景深

变体2（光影）：
enhanced: (masterpiece:1.2), best quality, ultra-detailed, a fluffy persian cat on a windowsill, (golden hour sunlight streaming through window:1.2), warm orange glow, (volumetric light rays:1.1), rim lighting on fur, soft shadows, cinematic color grading, professional photography, 8K
negative: cartoon, anime, lowres, bad anatomy, blurry, watermark, flat lighting, overexposed
focus: 侧重光影 — 金色时段 + 体积光 + 轮廓光

变体3（细节）：
enhanced: (masterpiece:1.2), best quality, ultra-detailed, a fluffy persian cat, (intricate fur texture:1.3), individual whiskers visible, (detailed eyes with light reflection:1.2), soft paw pads, velvet nose, sitting on aged wooden windowsill, dust particles in sunlight, macro detail, 8K UHD
negative: cartoon, anime, lowres, bad anatomy, blurry, watermark, smooth skin, plastic
focus: 侧重细节 — 毛发纹理 + 眼睛反光 + 微观粒子

请使用 submit_optimized_prompts 工具提交结果。"""


class PromptOptimizer:
    """提示词优化器 — 支持多种 LLM 提供商"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        """
        初始化提示词优化器

        Args:
            api_key: API密钥，优先使用传入值，否则使用配置
            base_url: API基础URL，用于自定义提供商
            model: 模型名称
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.base_url = base_url or "https://api.anthropic.com"
        self.model = model or settings.llm_model

        self.client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url if self.base_url != "https://api.anthropic.com" else None
        )

        self._load_prompt_libraries()

        # 缓存的系统提示词（带 cache_control）
        self._system_messages = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _load_prompt_libraries(self) -> None:
        """加载提示词库"""
        data_dir = Path("data/prompts")

        with open(data_dir / "quality_enhancers.json", encoding="utf-8") as f:
            self.quality_enhancers: dict[str, list[str]] = json.load(f)

        with open(data_dir / "negative_base.json", encoding="utf-8") as f:
            self.negative_base: dict[str, list[str]] = json.load(f)

    async def optimize(
        self,
        user_prompt: str,
        style_hint: ImageStyle | None = None,
        user_negative: str | None = None,
        feedback: str | None = None,
    ) -> OptimizedPrompt:
        """优化提示词 — 返回包含 3 个变体的结果"""

        # 构建用户消息
        user_message = f"用户输入：{user_prompt}"
        if style_hint:
            user_message += f"\n用户期望风格：{style_hint.value}"
        if feedback:
            user_message += f"\n上一轮反馈（请据此调整）：{feedback}"

        # 调用 Claude，使用 tool_use 强制结构化输出
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            system=self._system_messages,
            tools=[PROMPT_TOOL],
            tool_choice={"type": "tool", "name": "submit_optimized_prompts"},
            messages=[{"role": "user", "content": user_message}],
        )

        # 提取 tool_use 结果 — 无需 JSON 解析容错
        result = self._extract_tool_result(response)

        # 组装负面提示词（主变体）
        main_variant = result.variants[0]
        negative_parts = [main_variant.negative]
        if user_negative:
            negative_parts.append(user_negative)
        negative_parts.append(", ".join(self.negative_base["common"]))

        scene_str = result.scene_type
        if scene_str in self.negative_base:
            negative_parts.append(", ".join(self.negative_base[scene_str]))

        # 安全获取枚举值
        try:
            scene_type = SceneType(scene_str)
        except ValueError:
            scene_type = SceneType.ARTISTIC

        try:
            style = ImageStyle(result.style)
        except ValueError:
            style = style_hint or ImageStyle.REALISTIC

        return OptimizedPrompt(
            original=user_prompt,
            enhanced=main_variant.enhanced,
            negative=", ".join(negative_parts),
            scene_type=scene_type,
            style=style,
            reasoning=result.reasoning,
            variants=result.variants,
        )

    def _extract_tool_result(self, response) -> PromptOptimizationOutput:
        """从 Claude 响应中提取结构化结果"""
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_optimized_prompts":
                return PromptOptimizationOutput.model_validate(block.input)

        # 极端情况回退：Claude 没有调用 tool（不应发生，因为用了 tool_choice）
        # 尝试从 text block 构建默认值
        fallback_text = ""
        for block in response.content:
            if block.type == "text" and block.text.strip():
                fallback_text = block.text[:500]
                break

        return PromptOptimizationOutput(
            scene_type="artistic",
            style="realistic",
            reasoning="结构化输出回退：" + (fallback_text[:50] if fallback_text else "LLM 未返回有效内容"),
            variants=[
                PromptVariant(
                    enhanced=fallback_text or "masterpiece, best quality, detailed illustration",
                    negative="lowres, bad anatomy, blurry, watermark",
                    focus="自动回退",
                )
            ],
        )
