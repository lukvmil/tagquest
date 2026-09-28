import httpx

base_url = "http://127.0.0.1:8000"

resp = httpx.post(base_url + "/tag")
tag_id = resp.text
print(tag_id)