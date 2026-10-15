import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
col = client.get_collection("repo_index_9b645561")

results = col.get(limit=5, include=["documents", "metadatas"])

for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
    print(f"--- Chunk {i+1} ---")
    print(f"File    : {meta.get('file_path')}")
    print(f"Preview : {doc[:300]}")
    print()