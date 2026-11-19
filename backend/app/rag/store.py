# Chroma 封装，两个集合：regulations 与 cases
import chromadb

from ..core.config import settings

_client: chromadb.api.ClientAPI | None = None

COLLECTIONS = ("regulations", "cases")


def client() -> chromadb.api.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client


def collection(name: str = "regulations") -> chromadb.api.Collection:
    assert name in COLLECTIONS, f"unknown collection: {name}"
    return client().get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def upsert_chunks(coll_name: str, source_id: str, chunks: list[str],
                  metadatas: list[dict], embeddings: list[list[float]]) -> int:
    coll = collection(coll_name)
    ids = [f"{source_id}:{i}" for i in range(len(chunks))]
    for meta in metadatas:
        meta["source_id"] = source_id
    coll.upsert(ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
    return len(chunks)


def delete_source(source_id: str, coll_names: tuple[str, ...] = COLLECTIONS) -> int:
    removed = 0
    for name in coll_names:
        coll = collection(name)
        found = coll.get(where={"source_id": source_id}, include=[])
        if found["ids"]:
            coll.delete(ids=found["ids"])
            removed += len(found["ids"])
    return removed


def collection_count(coll_name: str = "regulations") -> int:
    return collection(coll_name).count()


def get_all(coll_name: str = "regulations", where: dict | None = None) -> dict:
    return collection(coll_name).get(where=where, include=["documents", "metadatas"])
