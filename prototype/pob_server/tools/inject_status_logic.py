import os

path = os.path.expanduser("~/pob_server/app.py")
with open(path, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if 'await self.send_message("ai_thought_chunk", text)' in line:
        # 插入嗅探逻辑
        indent = line[:line.find('await')]
        new_lines.append(f'{indent}# Sniff Time/Location\n')
        new_lines.append(f'{indent}import re\n')
        new_lines.append(f'{indent}t_match = re.search(r"(?:时间|Time)[：:]\s*(.+?)(?:\\\\n|$)", text)\n')
        new_lines.append(f'{indent}l_match = re.search(r"(?:地点|Location)[：:]\s*(.+?)(?:\\\\n|$)", text)\n')
        new_lines.append(f'{indent}if t_match or l_match:\n')
        new_lines.append(f'{indent}    meta = {{}}\n')
        new_lines.append(f'{indent}    if t_match: meta["time"] = t_match.group(1).strip()\n')
        new_lines.append(f'{indent}    if l_match: meta["location"] = l_match.group(1).strip()\n')
        new_lines.append(f'{indent}    await self.send_message("meta_update", "", **meta)\n')

with open(path, "w") as f:
    f.writelines(new_lines)
print("✅ Backend logic injected.")
