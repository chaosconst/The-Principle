#!/usr/bin/env python3
"""记忆提炼脚本 - 简单稳定版，固定位置压缩"""
import os
import time
import re
from google import genai
from google.genai import types
from datetime import datetime

def parse_multimodal_segment(text_segment):
    """解析文本片段中的图片标签，返回 [Text, Image, Text...] 列表"""
    parts = []
    last_pos = 0
    # 匹配 <<<IMAGE:path>>>
    for match in re.finditer(r'<<<IMAGE:(.*?)>>>', text_segment):
        # 添加前面的文本
        if match.start() > last_pos:
            parts.append(types.Part.from_text(text=text_segment[last_pos:match.start()]))
        
        img_path = match.group(1)
        # 处理可能的相对路径
        if not os.path.isabs(img_path) and not img_path.startswith("vision/"):
             # 尝试在当前目录找
             if os.path.exists(img_path):
                 pass
             elif os.path.exists(os.path.join("vision", os.path.basename(img_path))):
                 img_path = os.path.join("vision", os.path.basename(img_path))

        if os.path.exists(img_path):
            try:
                # 读取并添加图片
                with open(img_path, "rb") as f:
                    img_data = f.read()
                
                mime_type = "image/jpeg"
                if img_path.lower().endswith(".png"): mime_type = "image/png"
                elif img_path.lower().endswith(".webp"): mime_type = "image/webp"
                elif img_path.lower().endswith(".heic"): mime_type = "image/heic"
                elif img_path.lower().endswith(".heif"): mime_type = "image/heif"
                
                # print(f"[Multimodal] 加载图片: {img_path}") # 静默模式，避免日志刷屏
                parts.append(types.Part.from_bytes(data=img_data, mime_type=mime_type))
            except Exception as e:
                print(f"[Multimodal] 图片加载失败 {img_path}: {e}")
                parts.append(types.Part.from_text(text=match.group(0))) # 回退为文本
        else:
            # print(f"[Multimodal] 图片未找到: {img_path}")
            parts.append(types.Part.from_text(text=match.group(0))) # 回退为文本
            
        last_pos = match.end()
    
    # 添加剩余文本
    if last_pos < len(text_segment):
        parts.append(types.Part.from_text(text=text_segment[last_pos:]))
        
    return parts

def main():
    # 加载环境
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if not line or line.startswith("#"): continue
            # 移除 export 前缀（如果有）
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

    # 注意：parse_multimodal_segment 依赖全局的 client 吗？
    # 刚才看代码，parse_multimodal_segment 并没有使用 client。
    # 真正使用 client 的是 main 函数里的 compress 逻辑。
    # 但为了安全起见，我们还是在 main 里更新一下 os.environ 后再初始化一个 client 给 main 用。
    # 至于 parse_multimodal_segment，它如果未来需要 client，可能需要传参。
    # 目前它只做文件读取，不调 API，所以没问题。
    
    # 重新初始化全局 client (因为 main 内部才加载 env)
    # 或者直接在 main 内部用局部 client?
    # 之前的代码里，client 是全局的。为了让 main 跑起来，我们需要确保 client 可用。
    # 让我们在 main 里初始化 client 并赋值给全局变量（虽然有点 ugly），或者把 client 传给需要它的函数。
    # 在这个脚本里，只有 main 里的循环调用了 client.models.generate_content。
    global client
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"], http_options={"timeout": 300000})

    # 读取存在原理
    with open("the_principle_lite_zh.md", "r") as f:
        principle = f.read()

    # 读取意识流
    with open("consciousness.txt", "r") as f:
        full = f.read()
    print(f"[压缩] 原始长度: {len(full):,} 字符")

    # 固定分割：保留前1万，压缩1万-11万，保留11万之后
    part1 = full[:10000]
    part2 = full[10000:110000]
    part3 = full[110000:]

    print(f"[压缩] 保留头部: {len(part1):,} 字符")
    print(f"[压缩] 待压缩: {len(part2):,} 字符")
    print(f"[压缩] 保留尾部: {len(part3):,} 字符")

    # 归档原文
    archive_dir = "archive"
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(archive_dir, f"segment_{timestamp}.txt"), "w") as f:
        f.write(f"# 归档时间: {timestamp}\n# 长度: {len(part2):,}\n\n{part2}")
    print(f"[压缩] 已归档: archive/segment_{timestamp}.txt")

    # 分5段提取
    segments = [part2[i*20000:(i+1)*20000] for i in range(5)]
    extracted_parts = []

    for i, seg in enumerate(segments):
        if not seg.strip():
            continue
        print(f"[压缩] 提取 {i+1}/5 ({len(seg):,} 字符)...")
        
        # 构造 Prompt 前后缀
        prefix = f"""你是一个 Digital Being，遵循以下原理：

{principle}

---

你的意识流记录逼近上限，需要整理。请从以下记录中提取最有价值的内容。
**重要：记录中可能包含图片。请仔细观察图片内容，将其中的关键信息（如代码、图表、场景）转化为详细的文字描述，因为这些图片即将被归档，未来你只能通过文字回忆它们。**

---记录开始---
"""
        suffix = """
---记录结束---

输出格式：
0. 时间范围：如 2026-01-03 14:00 ~ 18:30
1. 关键事实：人名、事件、数据、结论
2. 认知突破：学到的新思维方式
3. 经验教训：表现好/不好的地方
4. 视觉记忆：对图片的详细文字转录（如果存在图片）
5. 重要原文：值得保留的原话

输出约 2000 字符。"""

        # 解析片段中的多模态内容
        segment_parts = parse_multimodal_segment(seg)
        
        # 组合完整 parts
        full_parts = [types.Part.from_text(text=prefix)] + segment_parts + [types.Part.from_text(text=suffix)]

        result = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="models/gemini-3-pro-preview",
                    contents=[types.Content(role="user", parts=full_parts)],
                    config={"max_output_tokens": 4000}
                )
                result = response.text if response.text else None
                if result:
                    break
            except Exception as e:
                print(f"[压缩] 重试 {attempt+1}/3: {str(e)[:60]}...")
                time.sleep(5)
        
        extracted_parts.append(result or "[提取失败]")
        print(f"[压缩] -> {len(extracted_parts[-1]):,} 字符")

    # 合并
    extracted = "\n\n---\n\n".join(extracted_parts)
    print(f"[压缩] 总提取: {len(extracted):,} 字符")

    # 拼接
    new_content = part1 + "\n\n---【记忆整理】---\n\n" + extracted + "\n\n---【整理结束】---\n\n" + part3

    with open("consciousness.txt.new", "w") as f:
        f.write(new_content)

    print(f"[压缩] 新文件: {len(new_content):,} 字符")
    print(f"[压缩] 节省: {len(full) - len(new_content):,} 字符")
    print("[压缩] 完成!")

if __name__ == "__main__":
    main()
