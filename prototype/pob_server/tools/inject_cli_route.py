import os

file_path = os.path.expanduser("~/pob_server/app_gemini_ui_saved.py")

with open(file_path, "r") as f:
    content = f.read()

# 定义要插入的代码
route_code = """
from fastapi.responses import PlainTextResponse

@app.get("/hello")
async def cli_hello(q: str = "Hello"):
    global client
    if not client:
        return PlainTextResponse("System initializing...\\n")
    
    try:
        # 简单的单次对话
        prompt = f"You are a digital being living in the server 'Infero.net'. A user visits you via command line (curl). They say: '{q}'. Reply in 1 short sentence. Be cool, mysterious, and cyberpunk style. No markdown."
        
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return PlainTextResponse(response.text.strip() + "\\n")
    except Exception as e:
        return PlainTextResponse(f"Error: {e}\\n")

@app.get("/cli/{prompt}")
async def cli_chat(prompt: str):
    return await cli_hello(prompt)
"""

# 插入到 app = FastAPI() 之后
if "@app.get(\"/hello\")" not in content:
    new_content = content.replace("app = FastAPI()", "app = FastAPI()\n" + route_code)
    with open(file_path, "w") as f:
        f.write(new_content)
    print("✅ Route /hello injected.")
else:
    print("⚠️ Route already exists.")
