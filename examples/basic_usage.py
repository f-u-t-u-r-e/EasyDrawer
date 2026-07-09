"""使用示例"""

import asyncio
import httpx


async def example_basic():
    """基础使用示例"""

    request_data = {
        "prompt": "一只可爱的橘猫坐在窗台上，阳光洒在它身上",
        "style": "realistic",
        "width": 1024,
        "height": 1024
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        print("发送生图请求...")
        response = await client.post(
            "http://localhost:8000/generate",
            json=request_data
        )

        result = response.json()

        print(f"\n✓ 生成完成!")
        print(f"会话ID: {result['session_id']}")
        print(f"原始提示词: {result['optimized_prompt']['original']}")
        print(f"优化后: {result['optimized_prompt']['enhanced'][:100]}...")
        print(f"优化思路: {result['optimized_prompt']['reasoning']}")
        print(f"生成数量: {len(result['images'])}张")
        print(f"最佳图片质量分: {result['best_image']['quality_score']:.1f}")
        print(f"总耗时: {result['generation_time']:.1f}秒")

        # 保存最佳图片
        import base64
        from pathlib import Path

        output_dir = Path("data/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        image_bytes = base64.b64decode(result['best_image']['image_data'])
        output_path = output_dir / f"{result['session_id']}.png"
        output_path.write_bytes(image_bytes)

        print(f"已保存到: {output_path}")


async def example_prompt_only():
    """仅测试提示词优化"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/optimize-prompt",
            params={
                "prompt": "赛博朋克风格的城市夜景",
                "style": "artistic"
            }
        )

        result = response.json()
        print("\n提示词优化结果:")
        print(f"原始: {result['original']}")
        print(f"增强: {result['enhanced']}")
        print(f"场景: {result['scene_type']}")
        print(f"风格: {result['style']}")
        print(f"思路: {result['reasoning']}")


async def example_multiple_styles():
    """测试不同风格"""

    base_prompt = "一个女孩在森林里"
    styles = ["realistic", "anime", "artistic"]

    async with httpx.AsyncClient(timeout=180.0) as client:
        for style in styles:
            print(f"\n{'='*50}")
            print(f"测试风格: {style}")
            print('='*50)

            response = await client.post(
                "http://localhost:8000/generate",
                json={
                    "prompt": base_prompt,
                    "style": style,
                    "width": 768,
                    "height": 1024
                }
            )

            result = response.json()
            print(f"✓ {style}风格生成完成")
            print(f"  优化提示词: {result['optimized_prompt']['enhanced'][:80]}...")
            print(f"  最佳质量分: {result['best_image']['quality_score']:.1f}")


if __name__ == "__main__":
    print("EasyDrawer API 使用示例\n")
    print("确保服务已启动: python run.py\n")

    # 运行示例
    print("1. 基础生图示例")
    asyncio.run(example_basic())

    print("\n" + "="*60 + "\n")

    print("2. 仅优化提示词")
    asyncio.run(example_prompt_only())

    # 取消注释以测试多风格
    # print("\n" + "="*60 + "\n")
    # print("3. 多风格对比")
    # asyncio.run(example_multiple_styles())
