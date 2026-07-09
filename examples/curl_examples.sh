"""curl使用示例"""

# 健康检查
curl http://localhost:8000/health

# 仅优化提示词
curl -X POST "http://localhost:8000/optimize-prompt?prompt=一只猫&style=realistic"

# 完整生图流程
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的橘猫坐在窗台上",
    "style": "realistic",
    "width": 1024,
    "height": 1024
  }'

# 艺术风格示例
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "赛博朋克风格的未来城市",
    "style": "artistic",
    "width": 1920,
    "height": 1080
  }'

# 动漫风格示例
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一个穿着校服的女孩在樱花树下",
    "style": "anime",
    "width": 768,
    "height": 1024
  }'
