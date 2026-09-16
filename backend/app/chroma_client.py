import chromadb

from app.config import settings

_client: chromadb.ClientAPI | None = None

COLLECTION_NAME = "symptom_taxonomy"


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_taxonomy_collection():
    # embedding_function=None: embeddings are always computed explicitly via the NVIDIA
    # client (see embed_taxonomy.py / symptom_match.py) rather than Chroma's own default
    # local model, so index-time and query-time embeddings come from the same source.
    # hnsw:space="cosine" makes Chroma return cosine distance (1 - cosine similarity), so
    # similarity = 1 - distance maps directly onto the embedding_similarity_threshold config.
    return get_chroma_client().get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=None, metadata={"hnsw:space": "cosine"}
    )
