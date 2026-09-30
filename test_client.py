import time

import httpx

base_url = "http://127.0.0.1:8000"

# tag_id = "QBWbLOb6tayxCNX-zvt3K"

resp = httpx.post(f"{base_url}/tag")
tag_id = resp.json()["id"]

print(tag_id)

httpx.post(
    url=f"{base_url}/tag/{tag_id}/entry",
    json={"text": "yo yo yo!"}
)

resp = httpx.get(url=f"{base_url}/tag/{tag_id}/entry")
print(resp.json())