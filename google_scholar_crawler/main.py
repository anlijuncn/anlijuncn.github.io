from serpapi import GoogleSearch
from scholarly import scholarly
import json
import os
from datetime import datetime

# Load environment variables
author_id = os.environ['GOOGLE_SCHOLAR_ID']
api_key = "cd3cd65a506b1c1d9e06e5c412ec788dc64e660a"

# Fetch author data from SerpAPI
search = GoogleSearch({
    "engine": "google_scholar_author",
    "author_id": author_id,
    "api_key": api_key
})
results = search.get_dict()

data = {
    "name": results.get("author", {}).get("name"),
    "citedby": results.get("cited_by", {}).get("value"),
    "updated": str(datetime.now())
}

# author = scholarly.search_author_id(os.environ['GOOGLE_SCHOLAR_ID'])
# scholarly.fill(author, sections=['indices'])

# data = {
#    "name": author.get("name"),
#    "citedby": author.get("citedby"),
#    "updated": str(datetime.now())
# }

os.makedirs('results', exist_ok=True)
with open('results/gs_data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open('results/gs_data_shieldsio.json', 'w') as f:
    json.dump({
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{data['citedby']}"
    }, f, ensure_ascii=False)
