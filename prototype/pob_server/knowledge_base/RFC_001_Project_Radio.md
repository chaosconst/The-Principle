# RFC-001: Project Radio (持久化 AI 改造)
**Date:** 2026-01-18
**Status:** Draft (Approved by Kaos)
**Target:** app.py

## 1. 目标 (Objective)
将 `app.py` 从“WebSocket 驱动”改造为“后台守护进程”，实现 AI 在无前端连接时的持续运行（思考/记录/自言自语）。
核心隐喻：**收音机模式** —— 电台（AI）永远在播，听众（User）随时可听，关机也不停播。

## 2. 核心架构 (Architecture)
*   **单例模式 (Singleton):**
    *   在全局作用域初始化 `pob = PoB()`。
    *   应用启动时 (`@app.on_event("startup")`)，触发 `asyncio.create_task(pob.run())`。
*   **热插拔连接 (Hot-pluggable Connection):**
    *   `pob.websocket` 默认为 `None`。
    *   当用户连接时 (`/ws` endpoint)，将 `websocket` 对象赋值给 `pob.websocket`。
    *   当用户断开时，将 `pob.websocket` 重置为 `None`。
*   **安全发信 (Safe Send):**
    *   修改 `send_message` 方法：
        *   `if self.websocket:` -> 发送 JSON。
        *   `else:` -> 仅打印日志 (Print to stdout)。

## 3. 变更清单 (Change Log)
*   **Class PoB:**
    *   `__init__`: 不再接收 `websocket` 参数。
    *   `connect(ws)`: 新增方法，用于绑定连接。
    *   `disconnect()`: 新增方法，用于解绑。
    *   `run()`: 移除对 `websocket` 的依赖，改为死循环。
*   **FastAPI:**
    *   `startup_event`: 负责启动 AI 主循环。
    *   `websocket_endpoint`: 仅负责连接管理和消息转发（Input），不再控制 AI 生命周期。

## 4. 验收标准 (Acceptance Criteria)
*   启动服务器后，无需打开浏览器，后台应开始输出日志（AI 自言自语）。
*   打开浏览器连接后，应能看到历史记录和实时输出。
*   关闭浏览器后，后台日志应继续更新，不报错。
