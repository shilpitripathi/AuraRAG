import os
import chromadb
from sentence_transformers import SentenceTransformer
import uuid
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")

# Create the ChromaDB client
# PersistenceClient stores the vector database on our computer
# This means our data remains even after we stop the server

client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

# Create or open our collection
# A collection is like a table/folder where we store document chunks, their embeddings, metadata.

collection = client.get_or_create_collection(
    name="aurarag_documents"
)

# Load the embedding model
# This model converts text into numerical vectors.

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# Store document chunks
def add_chunks(chunks: list[str], source: str):
    """convert document chunks into embeddings and store them in ChromaDB"""
    if not chunks:
        return 0

    # Prevent duplicate chunks accumulation if file is re-uploaded
    try:
        collection.delete(where={"source": source})
    except Exception:
        pass

    embeddings = embedding_model.encode(chunks).tolist()

    # Convert every chunk into vector
    ids = [
        str(uuid.uuid4())
        for _ in chunks
    ]

    # Store everything inside ChromaDB
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[
            {
                "source": source,
                "chunk_index": index
            }
            for index in range(len(chunks))
        ]
    )
    return len(chunks)

# Search for relevant chunks
def search_chunks(
    query: str,
    source: str | None = None,
    n_results: int = 6
):
    total = collection.count()
    if total == 0:
        return {"documents": [[]], "distances": [[]], "metadatas": [[]]}

    actual_k = min(n_results, total)
    query_embedding = embedding_model.encode(
        [query]
    ).tolist()

    where_filter = {"source": source} if source else None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=actual_k,
        where=where_filter,
        include=["documents", "distances", "metadatas"]
    )

    # Defensive validation: if source is specified, enforce that every chunk matches source
    if source and results.get("documents") and results.get("metadatas"):
        docs = results["documents"][0] if results["documents"] else []
        dists = results["distances"][0] if results.get("distances") and results["distances"] else [0.0] * len(docs)
        metas = results["metadatas"][0] if results["metadatas"] else []

        valid_docs = []
        valid_dists = []
        valid_metas = []

        for d, dist, m in zip(docs, dists, metas):
            if m and m.get("source") == source:
                valid_docs.append(d)
                valid_dists.append(dist)
                valid_metas.append(m)

        results["documents"] = [valid_docs]
        results["distances"] = [valid_dists]
        results["metadatas"] = [valid_metas]

    return results

def get_document_chunks(
    source: str | None = None,
    limit: int = 6
):
    """Retrieve document chunks for summary/overview queries."""

    if source:
        res = collection.get(
            where={"source": source},
            limit=limit,
            include=["documents", "metadatas"]
        )
        docs = res.get("documents", [])
        metas = res.get("metadatas", [])

        # Defensive validation & chronological sorting by chunk_index
        items = []
        for doc, meta in zip(docs, metas):
            if meta and meta.get("source") == source:
                chunk_idx = meta.get("chunk_index", 0)
                items.append((chunk_idx, doc))

        items.sort(key=lambda x: x[0])
        return [it[1] for it in items[:limit]]
    else:
        res = collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        return res.get("documents", [])