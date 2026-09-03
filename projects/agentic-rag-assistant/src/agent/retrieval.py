"""Retrieval layer: a thin, swappable wrapper around a local Chroma store.

The ``Retriever`` hides the embedding function and vector store behind
``ingest()`` and ``search()`` so the backend can be replaced without touching
any agent code.

# TODO: swap for a hosted embedding model + managed vector DB (e.g. a hosted
#       embedding API + Pinecone/pgvector) for scale and reproducibility.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.agent.config import get_settings


def _chunk(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    """Split text into ~``size``-char chunks, preferring paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        if buffer and len(buffer) + len(para) + 2 > size:
            chunks.append(buffer)
            buffer = ""
        if len(para) <= size:
            buffer = f"{buffer}\n\n{para}" if buffer else para
        else:
            # Hard-split an oversized paragraph into overlapping windows.
            if buffer:
                chunks.append(buffer)
                buffer = ""
            start = 0
            while start < len(para):
                chunks.append(para[start : start + size])
                start += max(1, size - overlap)
    if buffer:
        chunks.append(buffer)
    return chunks


class Retriever:
    """Local persistent Chroma retriever using Chroma's default embeddings.

    ``ingest`` and ``search`` are the only surface the rest of the app depends
    on, which is what makes the storage/embedding backend swappable.
    """

    def __init__(self, index_dir, collection_name: str, data_dir, k: int = 4) -> None:
        self.index_dir = Path(index_dir)
        self.collection_name = collection_name
        self.data_dir = Path(data_dir)
        self.k = k
        self._collection = None

    @property
    def collection(self):
        """Lazily open (or create) the Chroma collection.

        Chroma is imported lazily so importing this module stays cheap and does
        not require the vector DB to be installed (helpful for offline tests).
        """
        if self._collection is None:
            import chromadb

            self.index_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.index_dir))
            # get_or_create_collection uses Chroma's default embedding function.
            self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def count(self) -> int:
        """Number of chunks currently indexed."""
        return self.collection.count()

    def ingest(self, data_dir=None) -> int:
        """Read markdown docs, chunk them, and upsert into the vector store.

        Uses deterministic ids so re-running is idempotent.
        """
        source = Path(data_dir or self.data_dir)
        documents: list[str] = []
        ids: list[str] = []
        metadatas: list[dict] = []
        for path in sorted(source.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for i, chunk in enumerate(_chunk(text)):
                documents.append(chunk)
                ids.append(f"{path.stem}-{i}")
                metadatas.append({"source": path.name, "chunk": i})
        if not documents:
            return 0
        self.collection.upsert(documents=documents, ids=ids, metadatas=metadatas)
        return len(documents)

    def search(self, query: str, k: int | None = None) -> list[str]:
        """Return the top-k most relevant document chunks for ``query``."""
        result = self.collection.query(query_texts=[query], n_results=k or self.k)
        documents = result.get("documents") or [[]]
        return documents[0]


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    """Return a process-wide ``Retriever`` built from settings."""
    settings = get_settings()
    return Retriever(
        index_dir=settings.index_dir,
        collection_name=settings.collection_name,
        data_dir=settings.data_dir,
        k=settings.retrieval_k,
    )


if __name__ == "__main__":
    # `python -m src.agent.retrieval` (or `make ingest`) builds the index.
    ingested = get_retriever().ingest()
    print(f"Ingested {ingested} chunks into '{get_settings().collection_name}'.")
