# RFC-002: Centralized Toolchain Service (工具链微服务化)
**Date:** 2026-01-18
**Status:** Draft
**Target:** tools.infero.net (Port 8004)

## 1. 愿景 (Vision)
构建一个独立、无状态、标准化的 API 服务，为所有 Digital Beings (DBs) 提供底层能力支持（绘图、搜索、计算）。
DB 不再需要自己安装依赖或管理 API Key，只需向 Tools Service 发送请求。

## 2. 架构设计 (Architecture)
*   **协议:** RESTful API (HTTP/JSON).
*   **鉴权:** Bearer Token (仅限内部服务调用).
*   **部署:** 独立 Docker 容器 (`pob_tools_instance`).
*   **域名:** `tools.infero.net`.

## 3. 接口规范 (API Specification)

### 3.1 通用格式
*   **Request:** `POST /v1/{tool_name}`
*   **Header:** `Authorization: Bearer <INTERNAL_KEY>`

### 3.2 核心工具 (Core Tools)
1.  **Image Generation (/v1/paint)**
    *   Input: `{ "prompt": "...", "style": "cyberpunk" }`
    *   Output: `{ "image_url": "https://tools.infero.net/static/..." }`
2.  **Web Search (/v1/search)**
    *   Input: `{ "query": "...", "engine": "google" }`
    *   Output: `{ "results": [ { "title": "...", "link": "...", "snippet": "..." } ] }`
3.  **Code Execution (/v1/exec)** (高危，需慎重)
    *   Input: `{ "code": "...", "lang": "python" }`
    *   Output: `{ "stdout": "...", "stderr": "..." }`

## 4. 路线图 (Roadmap)
1.  **Phase 1:** 定义 API 接口文档 (OpenAPI/Swagger).
2.  **Phase 2:** 迁移现有脚本 (`pob_painter`, `pob_search`) 为 API 端点。
3.  **Phase 3:** 改造 DB (8003) 尝试调用新服务。
