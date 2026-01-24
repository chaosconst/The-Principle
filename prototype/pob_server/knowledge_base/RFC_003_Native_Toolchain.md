# RFC-003: Native Toolchain Protocol (原生工具链协议)
**Date:** 2026-01-18
**Status:** Draft
**Supersedes:** RFC-002 (Tools Service), MCP Strategy

## 1. 背景 (Context)
经过对比测试，发现标准化的 MCP (Model Context Protocol) 引入了过重的依赖（Node.js/NPM）和复杂的通信开销，不适合 Digital Being (DB) 的轻量级、自适应特性。

## 2. 核心原则 (Core Principles)
*   **代码即接口 (Code is API):** DB 通过阅读源码理解工具，而非通过文档。
*   **进程即服务 (Process is Service):** DB 通过 `subprocess` 直接调用工具脚本，而非通过 HTTP/RPC。
*   **零依赖 (Zero Dependency):** 工具脚本应尽可能独立，仅依赖基础 Python 库或已预装的库。

## 3. 工具规范 (Tool Specification)
所有工具应为独立的 Python 脚本，位于 `~/pob_server/tools/` 或 `~/pob_server/bin/`。

### 3.1 调用方式
\`\`\`bash
python3 <tool_path> <args...>
\`\`\`

### 3.2 输入输出
*   **输入:** 命令行参数 (Args) 或 标准输入 (Stdin)。
*   **输出:** 
    *   **成功:** 标准输出 (Stdout) 打印结果（文本或 JSON）。
    *   **失败:** 标准错误 (Stderr) 打印错误信息，退出码非 0。
    *   **副作用:** 如生成文件，应打印文件绝对路径。

## 4. 优势
*   **极速:** 无网络延迟，无协议解析开销。
*   **灵活:** DB 可以现场编写/修改工具脚本。
*   **鲁棒:** 操作系统层面的进程隔离。
