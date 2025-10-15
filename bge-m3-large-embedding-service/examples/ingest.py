
import os, json, requests

EMBED_URL = os.getenv("EMBED_URL", "http://localhost:8200/v1/embeddings")

docs = [
    {"title":"CI/CD 模板复用指南", "text":"共享流水线与模板化可以显著提升交付速度……", "tags":["cicd","devops"]},
    {"title":"Kafka 在 Teds 项目的用途", "text":"Kafka 用于事件驱动架构与日志回流……", "tags":["kafka","teds"]},
    {"title":"Linux 节点自动打补丁", "text":"通过自动化作业在非业务高峰进行滚动更新……", "tags":["linux","automation"]},
]

# 1) call embedding service
payload = {"model":"bge-m3-large","input":[d["text"] for d in docs]}
emb = requests.post(EMBED_URL, json=payload, timeout=120).json()
vecs = [item["embedding"] for item in emb["data"]]

# 2) write to Weaviate
import weaviate
client = weaviate.connect_to_local("http://localhost:8080")
coll = client.collections.get("Docs")

with coll.batch.dynamic() as b:
    for i, d in enumerate(docs):
        b.add_object(
            properties=d,
            vector=vecs[i]
        )
print("Ingested", len(docs))
client.close()
