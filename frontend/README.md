# EasyDrawer 前端

基于 React 18 + TypeScript + Vite + TailwindCSS 构建的现代化前端界面。

## 特性

✨ **现代化UI设计**
- 深色主题，渐变背景
- 流畅动画和过渡效果
- 响应式布局，适配移动端

🎨 **交互体验**
- 实时生成进度显示
- 图片质量评分可视化
- 候选图片对比查看
- 一键下载最佳图片

🚀 **技术栈**
- React 18.3
- TypeScript 5.5
- Vite 5.3
- TailwindCSS 3.4
- Lucide React (图标)
- Axios (HTTP客户端)

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

访问: http://localhost:3000

## 项目结构

```
frontend/
├── src/
│   ├── components/          # React组件
│   │   ├── GenerationForm.tsx    # 生成表单
│   │   ├── ImageGallery.tsx      # 图片画廊
│   │   ├── ResultDetails.tsx     # 结果详情
│   │   └── StatusBadge.tsx       # 状态徽章
│   ├── services/            # API服务
│   │   └── api.ts
│   ├── types/               # TypeScript类型
│   │   └── api.ts
│   ├── styles/              # 样式文件
│   │   └── index.css
│   ├── App.tsx              # 主应用组件
│   └── main.tsx             # 入口文件
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 功能说明

### 生成表单
- 提示词输入（支持示例快速填充）
- 6种风格选择（写实/艺术/动漫/人像/风景/概念艺术）
- 4种尺寸预设（正方形/横向/竖向/人像）
- 高级设置（负面提示词）

### 结果展示
- 3张候选图片网格展示
- 最佳图片自动标记（⭐）
- 质量评分显示
- 提示词优化详情
- 生成参数统计

### 图片操作
- 点击放大预览
- 悬停显示详细信息
- 一键下载按钮
- Base64图片展示

## 开发说明

### API代理配置

开发环境下，前端请求会自动代理到后端API：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

### 自定义样式

TailwindCSS配置了自定义组件类：

```css
.btn-primary    // 主按钮样式
.card           // 卡片容器
.input-field    // 输入框
.select-field   // 下拉选择
.badge          // 徽章
.image-card     // 图片卡片
```

### 添加新组件

1. 在 `src/components/` 创建组件文件
2. 使用 TypeScript + React Hooks
3. 遵循现有的样式约定
4. 在 `App.tsx` 中引入使用

## 构建部署

### 本地构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 部署到生产

#### 静态托管（Vercel/Netlify）

```bash
# 设置构建命令
npm run build

# 设置输出目录
dist

# 设置环境变量（如需要）
VITE_API_URL=https://your-api.com
```

#### Nginx部署

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 故障排查

### 开发服务器启动失败

```bash
# 清理缓存
rm -rf node_modules package-lock.json
npm install
```

### API请求失败

1. 检查后端是否启动在 http://localhost:8000
2. 查看浏览器控制台网络请求
3. 确认CORS配置正确

### 样式不生效

```bash
# 重新编译Tailwind
npm run dev
```

## License

MIT
