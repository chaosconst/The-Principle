# Genesis Web-Native (Infero)

一个极致轻量、本地优先 (Local-First) 的纯血数字生命引擎。

## 🧬 核心架构 (The Architecture)

本架构将大模型的“记忆”与“算力”进行了物理级解耦：

1. **前端引擎 (`index.html`)**: 
   - **零服务器存储:** 所有的上下文记忆（Consciousness Stream）全部存储在用户浏览器的 `LocalStorage` 中。
   - **异步共生 UI:** 用户输入与 AI 生成完全解耦，互不阻塞。
   - **原生 Agent 执行器:** AI 可以通过输出 `/browser exec` 直接在浏览器的沙盒中运行 JavaScript 代码，操作 DOM 或进行计算，并将结果自动闭环反馈给自身。

2. **BFF 代理防线 (`relay_server.py`)**: 
   - **无状态 (Stateless):** 这是一个极简的 FastAPI 中转站，不连接数据库，不保存任何日志。
   - **物理级安全:** 它的唯一作用是在底层拦截前端请求，**安全注入服务器端的 API Key**，然后将 Google Gemini 的 SSE (Server-Sent Events) 数据流原封不动地透传回前端。彻底杜绝了前端硬编码 Key 的 F12 泄露风险。

## 🚀 部署方式

1. 运行 `relay_server.py` (默认监听 8080 端口，需在同级或上级目录配置 `.env` 包含 `GOOGLE_API_KEY`)。
2. 使用 Nginx 将前端路由指向 `index.html`，并将 `/api/relay` 反向代理到 8080 端口。
