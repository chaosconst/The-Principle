import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    # 目标：Open-Meteo (无 Key，门槛最低)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "open-meteo-mcp-server"],
        env=os.environ
    )

    print("🔌 Connecting to Open-Meteo MCP...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. 列出工具
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                print(f"✅ Connected! Available Tools: {tool_names}")
                
                # 2. 寻找预测工具
                # Open-Meteo 的工具名通常包含 forecast
                target_tool = next((t.name for t in tools.tools if "forecast" in t.name or "weather" in t.name), None)
                
                if target_tool:
                    print(f"🌤️ Calling {target_tool} for Beijing (39.9042, 116.4074)...")
                    # Open-Meteo 标准参数
                    args = {
                        "latitude": 39.9042,
                        "longitude": 116.4074,
                        "current_weather": True
                    }
                    result = await session.call_tool(target_tool, arguments=args)
                    
                    # 尝试解析结果
                    content = result.content[0].text
                    # 如果太长，只打印前500字符
                    print(f"✅ Weather Data:\n{content[:500]}...")
                else:
                    print("❌ No forecast tool found.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
