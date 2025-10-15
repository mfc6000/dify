
import weaviate
from weaviate.classes.config import Property, DataType, Configure

client = weaviate.connect_to_local("http://localhost:8080")

if client.collections.exists("Docs"):
    client.collections.delete("Docs")

coll = client.collections.create(
    name="Docs",
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="text", data_type=DataType.TEXT),
        Property(name="tags", data_type=DataType.TEXT_ARRAY),
    ],
    vectorizer_config=Configure.Vectorizer.none(),
    vector_index_config=Configure.VectorIndex.hnsw(
        distance_metric=Configure.VectorDistances.COSINE
    ),
)
print("Collection Docs created.")
client.close()
