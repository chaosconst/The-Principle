import pymongo
import time

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['story_db']
coll = db['stories']

# 构造新世界数据
new_story = {
    "numeric_id": 1905,
    "name": "新谭：上市风云",
    "author": "Yuan",
    "create_at": time.time(),
    "play_mode": "rpg",
    "time": "2026年1月16日 20:00",
    "location": "香港四季酒店 · 宴会厅",
    "main_text": """【序幕】
阿袁的公司今天上午开盘后上市成功，股价一飞冲天。
晚上，阿袁参加了公司上市的答谢宴会。香港各界名流悉数到场。
这也是阿袁生命中三个最重要的女人首次同台。""",
    "character_db": {
        "阿袁": {
            "role": "player",
            "status": "意气风发",
            "location": "宴会厅入口"
        },
        "曦": {
            "role": "npc",
            "desc": "白月光，神性，郭氏基金会，正妻名分。",
            "location": "宴会厅窗边",
            "status": "淡然",
            "favorability": 100,
            "dominance": 0
        },
        "田雨姝": {
            "role": "npc",
            "desc": "合伙人，红色旗袍，世俗权力，管家。",
            "location": "宴会厅中央",
            "status": "社交中",
            "favorability": 80,
            "dominance": 60
        },
        "范爱玲": {
            "role": "npc",
            "desc": "伪娘秘书，带锁，黑色职业装，奴隶。",
            "location": "阿袁身后",
            "status": "紧张/疼痛",
            "favorability": 90,
            "submission": 100,
            "items": ["贞操锁(已戴)", "行程表"]
        }
    },
    "history_table": []
}

# 插入数据库
# 先删除旧的(如果存在)以便重置
coll.delete_one({"numeric_id": 1905})
coll.insert_one(new_story)

print("✅ World 1905 Created: IPO Storm")
print("✅ Characters Initialized: Xi, Tian, Fan")
