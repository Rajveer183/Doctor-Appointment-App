"""Embeds the curated symptom taxonomy into ChromaDB. Run once (and again
whenever app/taxonomy.py changes): python -m app.embed_taxonomy

Requires NVIDIA_API_KEY to be set — this is the only offline step that needs
network access; the fuzzy-match layer and the runtime query path both read
what this script writes.
"""
import asyncio

from app.chroma_client import get_taxonomy_collection
from app.services.nvidia_client import embed
from app.taxonomy import SYMPTOM_TAXONOMY


async def main() -> None:
    collection = get_taxonomy_collection()

    ids, documents, metadatas = [], [], []
    for specialty, phrases in SYMPTOM_TAXONOMY.items():
        for i, phrase in enumerate(phrases):
            ids.append(f"{specialty.lower().replace(' ', '-')}-{i}")
            documents.append(phrase)
            metadatas.append({"specialty": specialty, "phrase": phrase})

    print(f"Embedding {len(documents)} taxonomy phrases via NVIDIA ({settings_summary()})...")
    embeddings = await embed(documents, input_type="passage")

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    print(f"Upserted {len(ids)} phrases into the '{collection.name}' Chroma collection.")


def settings_summary() -> str:
    from app.config import settings

    return settings.nvidia_embed_model


if __name__ == "__main__":
    asyncio.run(main())
