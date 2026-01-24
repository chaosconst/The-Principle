import pymongo
import sys

client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
db = client['story_db']
collection = db['stories']

def print_story(doc):
    print(f"=== 📖 {doc.get('name', 'Untitled')} (ID: {doc.get('numeric_id', '?')}) ===")
    print(f"[简介]:\n{doc.get('prologue_and_characters', '')[:300]}...\n")
    print(f"[隐藏设定]:\n{doc.get('hidden-settings', '')[:300]}...\n")
    hist = doc.get('history_table', '')
    if hist:
        print("[历史摘要 (前5行)]:")
        for line in hist.strip().split('\n')[:5]:
            print(f"  {line}")
    print("-" * 40)

print("--- Inspecting ID 1896 ---")
doc_1896 = collection.find_one({"numeric_id": 1896})
if doc_1896:
    print_story(doc_1896)
else:
    print("ID 1896 not found.")

print("\n--- Searching for '山田凉子' ---")
doc_yamada = collection.find_one({"prologue_and_characters": {"$regex": "山田凉子"}})
if doc_yamada:
    print_story(doc_yamada)
else:
    print("Character '山田凉子' not found in prologue.")

