import pymongo
import sys

client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
db = client['story_db']
collection = db['stories']

print("scanning stories...")

stories = []
cursor = collection.find({}, {'name': 1, 'numeric_id': 1, 'history_table': 1})

for doc in cursor:
    hist = doc.get('history_table', '')
    if not hist:
        continue
    stories.append({
        'name': doc.get('name', 'Untitled'),
        'id': doc.get('numeric_id', '?'),
        'len': len(hist),
        'content': hist
    })

# 按长度降序排序
stories.sort(key=lambda x: x['len'], reverse=True)

print(f"Found {len(stories)} stories with history.\n")

# 获取 11-20 名
for i, s in enumerate(stories[10:20]):
    print(f"=== No.{i+11} {s['name']} (ID: {s['id']}) ===")
    print(f"[Length]: {s['len']} chars")
    print("[History Summary]:")
    for line in s['content'].strip().split('\n'):
        print(f"  {line}")
    print("\n" + "="*60 + "\n")

