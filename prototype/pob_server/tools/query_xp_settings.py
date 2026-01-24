import pymongo
import re

client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
db = client['story_db']
collection = db['stories']

# 关键词列表 (基于你的XP)
keywords = ["女犬", "调教", "控制", "奴", "项圈", "训练"]
regex = "|".join(keywords)

print(f"🔍 Searching for keywords: {keywords} ...\n")

# 查询包含关键词的故事
query = {
    "$or": [
        {"name": {"$regex": regex, "$options": "i"}},
        {"prologue_and_characters": {"$regex": regex, "$options": "i"}},
        {"hidden-settings": {"$regex": regex, "$options": "i"}}
    ]
}

cursor = collection.find(query).sort("updated_at", -1).limit(5)

for doc in cursor:
    print(f"=== 📖 {doc.get('name', '无题')} (ID: {doc.get('numeric_id', '?')}) ===")
    
    # 打印简介
    prologue = doc.get('prologue_and_characters', '')
    if prologue:
        print(f"[简介]:\n{prologue[:200]}...\n")
    
    # 打印隐藏设定 (这是重点)
    hidden = doc.get('hidden-settings', '')
    if hidden:
        print(f"[隐藏设定]:\n{hidden[:300]}...\n")
    
    print("-" * 40)

