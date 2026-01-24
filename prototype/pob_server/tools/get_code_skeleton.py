import ast
import sys

def get_skeleton(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception as e:
        return f"Error parsing file: {e}"

    skeleton = []
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            skeleton.append(f"class {node.name}:")
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    args = [a.arg for a in item.args.args]
                    skeleton.append(f"    def {item.name}({', '.join(args)}):")
                    # 提取 Docstring (如果有)
                    doc = ast.get_docstring(item)
                    if doc:
                        doc_line = doc.split('\n')[0] # 只取第一行
                        skeleton.append(f"        \"\"\" {doc_line} ... \"\"\"")
        elif isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            skeleton.append(f"def {node.name}({', '.join(args)}):")
            doc = ast.get_docstring(node)
            if doc:
                doc_line = doc.split('\n')[0]
                skeleton.append(f"    \"\"\" {doc_line} ... \"\"\"")

    return "\n".join(skeleton)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_code_skeleton.py <file_path>")
    else:
        print(get_skeleton(sys.argv[1]))
