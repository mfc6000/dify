
import os, requests, weaviate

EMBED_URL = os.getenv("EMBED_URL", "http://localhost:8200/v1/embeddings")

query_text = "Linux 自动打补丁"
payload = {"model":"bge-m3-large","input":query_text}
qv = requests.post(EMBED_URL, json=payload, timeout=60).json()["data"][0]["embedding"]

client = weaviate.connect_to_local("http://localhost:8080")
coll = client.collections.get("Docs")

res = coll.query.hybrid(
    query=query_text,
    vector=qv,
    alpha=0.5,
    limit=5,
    return_properties=["title","text","tags"]
)

for o in res.objects:
    print(o.properties["title"])
client.close()
