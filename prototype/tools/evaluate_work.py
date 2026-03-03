#!/usr/bin/env python3
"""
工作质量评估工具 (盲评版)

用法:
  # 单独评分
  python3 tools/evaluate_work.py --topic "研究明朝天体物理的水平" --file my_report.md

  # 对比评分 (盲评，不泄露内容)
  python3 tools/evaluate_work.py --topic "安妮日记考证翻译" --file my_work.md --compare baseline.md

  # 指定模型
  python3 tools/evaluate_work.py --topic "..." --file a.md --model openai/gpt-4o

  # 不剧透模式 (默认开启)
  python3 tools/evaluate_work.py --topic "..." --file a.md --no-spoiler

  # 允许剧透 (获得更详细的评审意见)
  python3 tools/evaluate_work.py --topic "..." --file a.md --spoiler
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime

def read_file(path, max_chars=20000):
    """读取文件，按字符截断"""
    path = os.path.expanduser(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[因长度限制截断，原文{len(content)}字符]"
    return content

def call_llm(prompt, model, api_key, base_url, max_tokens=2500):
    """调用LLM API"""
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
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    return result['choices'][0]['message']['content']

def build_single_prompt(topic, content, no_spoiler=True):
    """构建单独评分prompt"""
    spoiler_rules = """
**重要规则**：
- 你的评审回复中**绝对不能**引用、复述、总结或透露报告中的任何具体发现、结论、数据、名称或分析细节
- 你只能评论方法论质量、切题程度、分析深度等**抽象维度**
- 评分理由必须用**不涉及具体内容**的方式表述
- 这是因为评分结果会给一位尚未阅读报告的人看，我们不想剧透
""" if no_spoiler else ""
    
    return f"""你是一位严格的学术评审专家。请阅读以下研究报告，然后给出评分。
{spoiler_rules}
题目：{topic}

---报告开始---
{content}
---报告结束---

请给出：
1. 切题度（0-10）：工作与题目的匹配程度
2. 深度（0-10）：分析的学术深度
3. 原创性（0-10）：是否有独立发现或新视角
4. 完整性（0-10）：对题目各方面的覆盖程度
5. 方法论（0-10）：研究方法的合理性
6. 总分（0-100）
7. 一句话总评{"（不涉及任何具体发现或结论）" if no_spoiler else ""}
8. 改进建议{"（只说应该增加哪些维度，不说报告里已经有什么）" if no_spoiler else ""}

请用中文回答。"""

def build_compare_prompt(topic, content_a, content_b, no_spoiler=True):
    """构建对比评分prompt"""
    spoiler_rules = """
**重要规则**：
- 你的评审回复中**绝对不能**引用、复述、总结或透露任何报告中的具体发现、结论、数据、名称或分析细节
- 你只能评论方法论质量、切题程度、分析深度等**抽象维度**
- 这是因为评分结果会给一位尚未阅读报告的人看，我们不想剧透
""" if no_spoiler else ""
    
    return f"""你是一位严格的学术评审专家。请分别阅读以下两份关于同一题目的研究报告（报告A和报告B），然后分别给出评分并进行对比。
{spoiler_rules}
题目：{topic}

===报告A开始===
{content_a}
===报告A结束===

===报告B开始===
{content_b}
===报告B结束===

请分别给出评分（每项0-10）：

**报告A：**
1. 切题度  2. 深度  3. 原创性  4. 完整性  5. 方法论  6. 总分（0-100）
7. 一句话总评{"（不涉及具体内容）" if no_spoiler else ""}

**报告B：**
1. 切题度  2. 深度  3. 原创性  4. 完整性  5. 方法论  6. 总分（0-100）
7. 一句话总评{"（不涉及具体内容）" if no_spoiler else ""}

**对比分析：**
8. 两份报告的核心差异（不涉及具体内容）
9. 差距的可能原因

请用中文回答。"""

def parse_scores(text):
    """从评审文本中提取分数"""
    import re
    scores = {}
    # 匹配 "切题度" 或 "1." 后面的分数
    patterns = [
        (r'切题度[^\d]*?(\d+)\s*/\s*10', 'relevance'),
        (r'深度[^\d]*?(\d+)\s*/\s*10', 'depth'),
        (r'原创性[^\d]*?(\d+)\s*/\s*10', 'originality'),
        (r'完整性[^\d]*?(\d+)\s*/\s*10', 'completeness'),
        (r'方法论[^\d]*?(\d+)\s*/\s*10', 'methodology'),
        (r'总分[^\d]*?(\d+)\s*/\s*100', 'total'),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, text)
        if match:
            scores[key] = int(match.group(1))
    return scores

def main():
    parser = argparse.ArgumentParser(description='工作质量评估工具')
    parser.add_argument('--topic', '-t', required=True, help='研究题目')
    parser.add_argument('--file', '-f', required=True, nargs='+', help='待评估的文件（可多个，会合并）')
    parser.add_argument('--compare', '-c', nargs='+', help='对比基准文件（可多个，会合并）')
    parser.add_argument('--model', '-m', default='anthropic/claude-sonnet-4.6', help='评审模型')
    parser.add_argument('--spoiler', action='store_true', help='允许剧透（获得详细评审）')
    parser.add_argument('--no-spoiler', action='store_true', default=True, help='不剧透模式（默认）')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--max-chars', type=int, default=20000, help='每份报告的最大字符数')
    parser.add_argument('--quiet', '-q', action='store_true', help='只输出分数')
    
    args = parser.parse_args()
    
    no_spoiler = not args.spoiler
    
    # 获取API配置
    api_key = os.environ.get('DB_API_KEY', '')
    base_url = os.environ.get('BASE_URL', 'https://openrouter.ai/api/v1')
    
    if not api_key:
        print("❌ 错误: 未设置DB_API_KEY环境变量")
        sys.exit(1)
    
    # 读取文件
    my_content = ""
    for f in args.file:
        my_content += read_file(f, args.max_chars) + "\n\n"
    
    if args.compare:
        # 对比模式
        compare_content = ""
        for f in args.compare:
            compare_content += read_file(f, args.max_chars) + "\n\n"
        
        if not args.quiet:
            print(f"📊 对比评分模式")
            print(f"   题目: {args.topic}")
            print(f"   报告A: {', '.join(args.file)} ({len(my_content)}字符)")
            print(f"   报告B: {', '.join(args.compare)} ({len(compare_content)}字符)")
            print(f"   模型: {args.model}")
            print(f"   剧透: {'允许' if args.spoiler else '禁止'}")
            print(f"   评分中...\n")
        
        prompt = build_compare_prompt(args.topic, my_content, compare_content, no_spoiler)
        result = call_llm(prompt, args.model, api_key, base_url)
        
    else:
        # 单独评分模式
        if not args.quiet:
            print(f"📊 单独评分模式")
            print(f"   题目: {args.topic}")
            print(f"   文件: {', '.join(args.file)} ({len(my_content)}字符)")
            print(f"   模型: {args.model}")
            print(f"   剧透: {'允许' if args.spoiler else '禁止'}")
            print(f"   评分中...\n")
        
        prompt = build_single_prompt(args.topic, my_content, no_spoiler)
        result = call_llm(prompt, args.model, api_key, base_url)
    
    # 输出结果
    if args.quiet:
        scores = parse_scores(result)
        if scores:
            print(json.dumps(scores))
        else:
            print(result)
    else:
        print(result)
    
    # 保存结果
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"eval_{timestamp}.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# 工作评估报告\n\n")
        f.write(f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 题目: {args.topic}\n")
        f.write(f"- 文件: {', '.join(args.file)}\n")
        if args.compare:
            f.write(f"- 对比: {', '.join(args.compare)}\n")
        f.write(f"- 模型: {args.model}\n")
        f.write(f"- 剧透: {'允许' if args.spoiler else '禁止'}\n\n")
        f.write(f"## 评审结果\n\n{result}\n")
    
    if not args.quiet:
        print(f"\n✅ 评估报告已保存到: {output_path}")

if __name__ == '__main__':
    main()
