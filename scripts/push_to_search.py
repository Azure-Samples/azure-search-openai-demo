import uuid
import requests
import os
import json

def push_to_search(chunk):
    endpoint = os.getenv("SEARCH_ENDPOINT")  # Ej: https://<search-name>.search.windows.net
    api_key = os.getenv("SEARCH_KEY")
    index_name = os.getenv("SEARCH_INDEX")

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    payload = {
        "value": [{
            "@search.action": "mergeOrUpload",
            "id": str(uuid.uuid4()),
            "content": chunk["text"],
            "rol": chunk["metadata"]["rol"],
            "archivo": chunk["metadata"]["archivo"],
            "origen": chunk["metadata"]["origen"]
        }]
    }

    url = f"{endpoint}/indexes/{index_name}/docs/index?api-version=2021-04-30-Preview"
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        print(f"📥 Indexado: {chunk['metadata']['archivo']} → {chunk['metadata']['rol']}")
    else:
        print(f"⚠️ Error indexando: {response.text}")