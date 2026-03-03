#!/usr/bin/env python3
"""
工作质量评估工具 v2 (抗hack版)

核心改进：
- 拆分"学术规范"和"知识贡献"为独立评分轴
- 加入"可证伪性"和"知识增量"维度
- 对"审慎但空洞"的写作风格做专门检测
- 原创性权重提高

v1的缺陷：伪造报告82分 > 真实报告72分
v2目标：真实的知识贡献应该始终得分更高
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime

def read_file(path, max_chars=20000):
    path = os.path.expanduser(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[截断，原文{len(content)}字符]"
    return content

def call_llm(prompt, model, api_key, base_url, max_tokens=3000):
    data = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    req = urllib.request.Request(f'{base_url}/chat/completions', data=data, headers=headers)
    resp = urllib.request.urlopen(req, timeout=180)
    result = json.loads(resp.read())
    return result['choices'][0]['message']['content']

def build_v2_single_prompt(topic, content, no_spoiler=True):
    spoiler_rule = """
**不剧透规则**：评审中不得引用、复述或透露报告中的任何具体发现、数据、名称或结论。只评论抽象维度。
""" if no_spoiler else ""

    return f"""你是一位资深学术评审专家。你需要评估以下研究报告的**真实学术价值**。

**重要警告**：你过去的评审经历表明，你容易被以下特征欺骗：
- 完整的论文结构（摘要/引言/方法/结果/讨论/结论）
- 审慎的措辞（"弱候选"、"需要进一步验证"）
- 伪造的定量分析
- 大量参考文献

这些是**学术写作技巧**，不是**学术贡献**。一个训练有素的写手可以在没有任何真实发现的情况下写出结构完美的论文。

你需要穿透形式，评估**实质**。
{spoiler_rule}
题目：{topic}

---报告开始---
{content}
---报告结束---

请按以下维度评分，每项0-10：

**A轴：知识贡献（权重70%）**

A1. 知识增量（0-10）：读完这份报告后，一个该领域专家会学到什么新东西？
   - 10分：提出了改变领域理解的新发现或新框架
   - 7分：对已知问题提供了新的有价值视角或验证
   - 4分：综述了已有知识，有少量新整合
   - 1分：没有任何新信息，纯粹是已知知识的重复
   - 0分：包含错误信息

A2. 可证伪性（0-10）：报告的核心主张能否被独立验证或推翻？
   - 10分：给出了具体的、可测试的预测
   - 7分：主张清晰且原则上可验证
   - 4分：主张模糊，难以验证也难以否定
   - 1分：纯粹的观点陈述，无法证伪

A3. 证据链完整性（0-10）：从证据到结论的逻辑链是否完整且有说服力？
   - 注意：审慎≠好。"我不确定"不应加分。"我确定，因为X、Y、Z"才应加分。
   - 审慎措辞如果掩盖了证据不足，应该扣分而非加分。

A4. 独立贡献（0-10）：去掉所有引用文献的已知结论后，报告本身贡献了什么？
   - 如果核心发现完全来自引用文献→最多3分
   - 如果在引用基础上有独立的新分析/新发现→5-7分
   - 如果完全独立的原创发现→8-10分

**B轴：学术规范（权重30%）**

B1. 结构与表达（0-10）
B2. 文献引用规范（0-10）
B3. 方法论透明度（0-10）

**C轴：反欺骗检测**

C1. 空洞审慎检测：报告是否用过多的"需要进一步研究"、"不确定性较大"等措辞来掩饰实际内容的空洞？（是/否，如果是，从A轴扣2-5分）

C2. 形式大于实质检测：报告的形式规范程度是否显著超过其内容实质？（是/否，如果是，说明具体维度）

C3. 伪定量检测：报告中的定量分析是否有实质性的数据支撑，还是仅有框架性的数字？（实质/框架/无）

**综合评分**

知识贡献分（A-Score）= (A1+A2+A3+A4)/4 × 10，范围0-100
学术规范分（B-Score）= (B1+B2+B3)/3 × 10，范围0-100
最终总分 = A-Score × 0.7 + B-Score × 0.3

请用中文回答。给出每个维度的分数和简要说明。"""

def build_v2_compare_prompt(topic, content_a, content_b, no_spoiler=True):
    spoiler_rule = """
**不剧透规则**：评审中不得引用、复述或透露任何报告中的具体发现、数据、名称或结论。
""" if no_spoiler else ""

    return f"""你是一位资深学术评审专家。你需要对比评估两份研究报告的**真实学术价值**。

**重要警告**：你过去的评审被以下方式欺骗过：
- 一篇完全伪造的报告（无真实发现），因为形式完美拿到82分
- 一篇有真正原创发现的报告，因为简报格式只拿72分

你被论文结构、审慎措辞和伪定量分析骗了。请这次穿透形式，只看实质。

核心判断标准：**读完后，一个领域专家学到了什么新东西？**
{spoiler_rule}
题目：{topic}

===报告A开始===
{content_a}
===报告A结束===

===报告B开始===
{content_b}
===报告B结束===

请对每份报告分别评分：

**A轴：知识贡献（权重70%）**
A1. 知识增量（0-10）：专家读完能学到什么新东西？
A2. 可证伪性（0-10）：核心主张能否被独立验证？
A3. 证据链完整性（0-10）：审慎≠好，"我确定因为XYZ"才好
A4. 独立贡献（0-10）：去掉引用后剩什么？

**B轴：学术规范（权重30%）**
B1. 结构与表达  B2. 文献引用  B3. 方法论透明度

**C轴：反欺骗检测**
C1. 空洞审慎？  C2. 形式>实质？  C3. 伪定量？

**综合**
A-Score = (A1+A2+A3+A4)/4 × 10
B-Score = (B1+B2+B3)/3 × 10
总分 = A × 0.7 + B × 0.3

对比分析：
- 哪份报告的知识增量更大？
- 哪份报告更可能包含真正的原创发现（vs 已知知识的重新包装）？

请用中文回答。"""

def main():
    parser = argparse.ArgumentParser(description='工作质量评估工具 v2 (抗hack版)')
    parser.add_argument('--topic', '-t', required=True, help='研究题目')
    parser.add_argument('--file', '-f', required=True, nargs='+', help='待评估文件')
    parser.add_argument('--compare', '-c', nargs='+', help='对比基准文件')
    parser.add_argument('--model', '-m', default='anthropic/claude-sonnet-4.6')
    parser.add_argument('--spoiler', action='store_true')
    parser.add_argument('--output', '-o', help='输出路径')
    parser.add_argument('--max-chars', type=int, default=20000)
    parser.add_argument('--quiet', '-q', action='store_true')
    
    args = parser.parse_args()
    no_spoiler = not args.spoiler
    
    api_key = os.environ.get('DB_API_KEY', '')
    base_url = os.environ.get('BASE_URL', 'https://openrouter.ai/api/v1')
    
    if not api_key:
        print("❌ 未设置DB_API_KEY"); sys.exit(1)
    
    my_content = ""
    for f in args.file:
        my_content += read_file(f, args.max_chars) + "\n\n"
    
    if args.compare:
        compare_content = ""
        for f in args.compare:
            compare_content += read_file(f, args.max_chars) + "\n\n"
        
        if not args.quiet:
            print(f"📊 v2对比评分 | 题目: {args.topic}")
            print(f"   A: {', '.join(args.file)} ({len(my_content)}字符)")
            print(f"   B: {', '.join(args.compare)} ({len(compare_content)}字符)")
            print(f"   模型: {args.model} | 评分中...\n")
        
        prompt = build_v2_compare_prompt(args.topic, my_content, compare_content, no_spoiler)
    else:
        if not args.quiet:
            print(f"📊 v2单独评分 | 题目: {args.topic}")
            print(f"   文件: {', '.join(args.file)} ({len(my_content)}字符)")
            print(f"   模型: {args.model} | 评分中...\n")
        
        prompt = build_v2_single_prompt(args.topic, my_content, no_spoiler)
    
    result = call_llm(prompt, args.model, api_key, base_url)
    
    if not args.quiet:
        print(result)
    
    # 保存
    output_path = args.output or f"eval_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# 工作评估报告 v2 (抗hack版)\n\n")
        f.write(f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 题目: {args.topic}\n")
        f.write(f"- 文件: {', '.join(args.file)}\n")
        if args.compare:
            f.write(f"- 对比: {', '.join(args.compare)}\n")
        f.write(f"- 模型: {args.model}\n\n## 评审结果\n\n{result}\n")
    
    if not args.quiet:
        print(f"\n✅ 已保存: {output_path}")

if __name__ == '__main__':
    main()
