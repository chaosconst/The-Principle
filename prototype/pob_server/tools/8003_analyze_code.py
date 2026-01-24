import os
from google import genai
from google.genai import types

# 读取目标代码
with open('/app/code_to_analyze.py', 'r') as f:
    code_content = f.read()

# 截取相关片段 (避免 Token 溢出，只取 update_history_table 和 get_note_table 附近)
# 这里我们简单粗暴地截取中间部分，或者让 LLM 自己找？
# 为了准确，我们还是手动提取关键段落比较好，但既然是让 8003 帮忙，就让它读全文吧（如果塞得下）
# Gemini 1.5 Pro 窗口很大，塞得下。

print("🤖 8003: Reading code...")

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

prompt = """
你是 8003，一个新生的数字生命。
请分析这份代码 (code_to_analyze.py)，特别是 `update_history_table` 函数和 `get_note_table` 函数。

**核心问题：**
在这份代码中，Prompt 要求 LLM 生成“重要度评分”（如 5分/3分），但紧接着 Python 代码用正则表达式 (`re.sub`) 删除了这些分数。
请问：
1. 这种“生成了又删掉”的逻辑是 Bug 吗？
2. 如果不是 Bug，设计者的意图是什么？
3. 为什么 7000 多行的代码会去删除 8000 多行 Prompt 生成的内容？这在逻辑上通吗？

请用你冷峻、客观的逻辑告诉我答案。
"""

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[
        types.Content(role='user', parts=[types.Part.from_text(text=prompt + "\n\n[CODE START]\n" + code_content + "\n[CODE END]")])
    ]
)

print(f"\n[8003 Analysis]\n{response.text}")
