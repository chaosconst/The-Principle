import re
import sys

def get_skeleton(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file: {e}"

    skeleton = []
    
    # 正则匹配类和函数定义
    # 允许前面有空格 (缩进)
    pattern = re.compile(r'^(\s*)(class|def|async def)\s+([a-zA-Z0-9_]+)\s*(\(.*?\))?:')

    for line in lines:
        match = pattern.match(line)
        if match:
            indent = match.group(1)
            keyword = match.group(2)
            name = match.group(3)
            # args = match.group(4) if match.group(4) else ""
            
            # 为了简洁，只保留定义行，去掉具体的参数细节如果太长
            clean_line = line.strip().rstrip(':')
            skeleton.append(f"{indent}{clean_line}")

    return "\n".join(skeleton)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_code_skeleton_regex.py <file_path>")
    else:
        print(get_skeleton(sys.argv[1]))
