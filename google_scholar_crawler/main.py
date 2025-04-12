from scholarly import scholarly
import json
import os
from datetime import datetime

# 获取作者基本信息和引用数
author = scholarly.search_author_id(os.environ['GOOGLE_SCHOLAR_ID'])
scholarly.fill(author, sections=['indices', 'counts'])

# 构造数据
author_info = {
    "name": author.get("name"),
    "citedby": author.get("citedby"),
    "updated": str(datetime.now())
}

# 保存结果
os.makedirs('results', exist_ok=True)
with open('results/gs_data.json', 'w') as f:
    json.dump(author_info, f, ensure_ascii=False, indent=2)

# 生成 shields.io JSON 数据
shieldio_data = {
    "schemaVersion": 1,
    "label": "citations",
    "message": f"{author_info['citedby']}"
}
with open('results/gs_data_shieldsio.json', 'w') as f:
    json.dump(shieldio_data, f, ensure_ascii=False)
