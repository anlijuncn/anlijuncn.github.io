from scholarly import scholarly
import json
import os
from datetime import datetime

author = scholarly.search_author_id(os.environ['GOOGLE_SCHOLAR_ID'])
scholarly.fill(author, sections=['indices', 'counts'])

data = {
    "name": author.get("name"),
    "citedby": author.get("citedby"),
    "updated": str(datetime.now())
}

os.makedirs('results', exist_ok=True)
with open('results/gs_data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open('results/gs_data_shieldsio.json', 'w') as f:
    json.dump({
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{data['citedby']}"
    }, f, ensure_ascii=False)
