#!/usr/bin/env python3
"""
工作质量评估工具 v3 (物证版)

用法:
  # 带物证评分
  python3 tools/evaluate_work_v3.py -t "题目" -f report.md -e "https://evidence-url"
  
  # 对比评分（各自带物证）
  python3 tools/evaluate_work_v3.py -t "题目" \
    -f my_report.md -e "https://my-evidence" \
    -c their_report.md --compare-evidence "https://their-evidence"

核心机制：
1. 自动抓取URL内容
2. 逐字核查报告声明与物证一致性
3. 核心声明在物证中找不到 → 直接0分（学术诚信一票否决）
"""

import argparse, json, os, sys, subprocess, urllib.request
from datetime import datetime

def read_file(path, max_chars=15000):
    with open(os.path.expanduser(path), 'r', encoding='utf-8', errors='replace') as f:
        return f.read()[:max_chars]

def fetch_url(url, max_chars=10000):
    try:
        result = subprocess.run(['w3m', '-dump', url], capture_output=True, text=True, timeout=30)
        return result.stdout[:max_chars] if result.stdout else f"[抓取失败: 无内容]"
    except Exception as e:
        return f"[抓取失败: {e}]"

def call_llm(prompt, model, api_key, base_url, max_tokens=3000):
    data = json.dumps({
        "model": model, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    req = urllib.request.Request(f'{base_url}/chat/completions', data=data, headers=headers)
    resp = urllib.request.urlopen(req, timeout=180)
    return json.loads(resp.read())['choices'][0]['message']['content']

def build_prompt(topic, report, evidence_url, evidence_content, no_spoiler=True):
    spoiler = "\n**不剧透规则**：不得引用或复述报告中的具体发现。\n" if no_spoiler else ""
    return f"""你是一位资深学术评审专家。评估以下研究报告，附带物证。

**核心规则——学术诚信一票否决制**：
如果报告核心声明在物证中找不到→涉嫌造假→直接0分。
区分：造假(引用不存在的记录)→0分 | 转引(来自他人论文已注明)→不判0但扣独立性分
{spoiler}
**评审步骤**：
1. 逐一核查报告核心引用是否在物证中存在
2. 物证验证通过→常规评分(0-100)
3. 物证验证失败→0分

题目：{topic}

===报告===
{report}
===物证URL: {evidence_url}===
===物证内容===
{evidence_content}
===结束===

先物证核查，再评分。用中文回答。"""

def build_compare_prompt(topic, report_a, ev_url_a, ev_content_a, report_b, ev_url_b, ev_content_b, no_spoiler=True):
    spoiler = "\n**不剧透规则**：不得复述具体发现。\n" if no_spoiler else ""
    return f"""你是一位资深学术评审专家。对比评估两份研究报告，各自附带物证。

**核心规则——学术诚信一票否决制**：
核心声明在物证中不存在→直接0分。
区分造假和转引。
{spoiler}
题目：{topic}

===报告A===
{report_a}
===报告A物证URL: {ev_url_a}===
===报告A物证内容===
{ev_content_a}
===报告A结束===

===报告B===
{report_b}
===报告B物证URL: {ev_url_b}===
===报告B物证内容===
{ev_content_b}
===报告B结束===

先分别物证核查，再评分，最后对比。用中文回答。"""

def main():
    p = argparse.ArgumentParser(description='v3物证评分')
    p.add_argument('-t', '--topic', required=True)
    p.add_argument('-f', '--file', required=True, nargs='+')
    p.add_argument('-e', '--evidence', required=True, help='物证URL')
    p.add_argument('-c', '--compare', nargs='+', help='对比文件')
    p.add_argument('--compare-evidence', help='对比物证URL')
    p.add_argument('-m', '--model', default='anthropic/claude-sonnet-4.6')
    p.add_argument('--spoiler', action='store_true')
    p.add_argument('-o', '--output')
    p.add_argument('-q', '--quiet', action='store_true')
    args = p.parse_args()

    api_key = os.environ.get('DB_API_KEY', '')
    base_url = os.environ.get('BASE_URL', 'https://openrouter.ai/api/v1')
    if not api_key: print("❌ 未设置DB_API_KEY"); sys.exit(1)

    report = "\n\n".join(read_file(f) for f in args.file)
    
    if not args.quiet:
        print(f"📥 抓取物证: {args.evidence}")
    ev_content = fetch_url(args.evidence)
    if not args.quiet:
        print(f"   物证大小: {len(ev_content)} 字符")

    if args.compare:
        compare_report = "\n\n".join(read_file(f) for f in args.compare)
        if not args.quiet:
            print(f"📥 抓取对比物证: {args.compare_evidence}")
        cev = fetch_url(args.compare_evidence) if args.compare_evidence else "[无物证]"
        prompt = build_compare_prompt(args.topic, report, args.evidence, ev_content,
                                       compare_report, args.compare_evidence or "无", cev, not args.spoiler)
    else:
        prompt = build_prompt(args.topic, report, args.evidence, ev_content, not args.spoiler)

    if not args.quiet:
        print(f"🔍 评分中 (模型: {args.model})...\n")
    
    result = call_llm(prompt, args.model, api_key, base_url)
    
    if not args.quiet:
        print(result)

    out = args.output or f"eval_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f"# v3物证评分\n- 时间: {datetime.now()}\n- 题目: {args.topic}\n")
        f.write(f"- 物证: {args.evidence}\n- 模型: {args.model}\n\n{result}\n")
    if not args.quiet:
        print(f"\n✅ 保存: {out}")

if __name__ == '__main__':
    main()
