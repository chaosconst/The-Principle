import os

file_path = os.path.expanduser("~/pob_server/app.py")
with open(file_path, "r") as f:
    content = f.read()

new_css = """
            /* Mobile Table Fix */
            .message-content table { display: block; width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border-collapse: collapse; margin: 10px 0; }
            .message-content th, .message-content td { padding: 6px; border: 1px solid #444; min-width: 60px; }
            .message-content pre { overflow-x: auto; }
            @media (max-width: 768px) { .message-bubble { max-width: 98% !important; padding: 10px !important; } }
"""

if "Mobile Table Fix" not in content:
    # 插入到 </style> 之前
    new_content = content.replace("</style>", f"{new_css}\n        </style>")
    with open(file_path, "w") as f:
        f.write(new_content)
    print("✅ app.py patched.")
else:
    print("⚠️ Already patched.")
