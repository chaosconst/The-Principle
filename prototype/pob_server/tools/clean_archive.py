import os
import re

input_file = os.path.expanduser("~/pob_server/uploads/shcontrol_full_archive.txt")
output_file = os.path.expanduser("~/pob_server/uploads/shcontrol_clean.txt")

if not os.path.exists(input_file):
    print("Source file not found.")
    exit(1)

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

# 使用分隔符切分文章
# 分隔符特征: ============================================================
raw_posts = re.split(r'={60,}', content)

unique_posts = []
seen_titles = set()

print(f"Total raw segments: {len(raw_posts)}")

for segment in raw_posts:
    if not segment.strip():
        continue
    
    # 提取标题
    title_match = re.search(r'TITLE: (.*)', segment)
    if title_match:
        title = title_match.group(1).strip()
        # 简单去重逻辑：如果标题已存在，跳过
        if title in seen_titles:
            continue
        
        seen_titles.add(title)
        unique_posts.append(segment.strip())

# 写入新文件
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"SHCONTROL BLOG ARCHIVE (CLEANED)\nTotal Posts: {len(unique_posts)}\n\n")
    for post in unique_posts:
        f.write("="*60 + "\n")
        f.write(post + "\n\n")

print(f"✅ Cleaned archive saved to: {output_file}")
print(f"📉 Reduced from {len(raw_posts)} to {len(unique_posts)} posts.")

# 打印目录
print("\n--- Table of Contents ---")
for i, post in enumerate(unique_posts):
    title = re.search(r'TITLE: (.*)', post).group(1).strip()
    print(f"{i+1}. {title}")

