# 新谭系统 (System 2) 核心架构分析
**Date:** 2026-01-16
**Source:** ~/Projects/futureGPT/src/umt_struct.py

## 1. 驱动核心 (Driving Core)
*   **Prompt 变量:** `WRITER_PROMPT`
*   **核心指令:** "你是一个网络小说作家，你的特点是充分揭露人性复杂黑暗... 尽量真实的推演..."
*   **生效机制:** 硬编码。

## 2. 逻辑流 (Logic Flow)
1.  **初始化:** 默认 `writer` 模式为 `detailed`。
2.  **Prompt 选择:**
    *   若 `writer == 'detailed'` 且 `enable_prompt_cache == True`:
    *   **强制使用** `WRITER_PROMPT`。
3.  **结果:** 无论用户是否干预，系统默认倾向于生成**黑暗、真实、细节密集**的剧情。

## 3. 结论
*   **风格来源:** 并非随机涌现，而是**初始参数 (Initial Parameters)** 的必然结果。
*   **系统性质:** 一个**反乌托邦模拟器**，旨在通过极端环境测试人性底线。
