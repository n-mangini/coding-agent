"""Vector store sobre Chroma para el pipeline RAG.

`RagStore` guarda chunks con sus embeddings (`text-embedding-3-small`) en una
colección persistente de Chroma y los consulta por similitud, devolviendo cada
hit con su fuente. `make_rag_store` es la fábrica con degradación elegante: si
`chromadb` no está instalado devuelve None, y la tool `retrieve` que se arma
encima queda como stub (mismo patrón que `make_web_search` sin `TAVILY_API_KEY`).
"""

import os

from .chunking import chunk_text
from .embeddings import embed_texts

DEFAULT_PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", "./rag_store")
COLLECTION_NAME = "rag_docs"


class RagStore:
    """Colección de Chroma más el cliente OpenAI que embebe chunks y consultas.

    Args:
        client: cliente OpenAI compartido (para generar embeddings).
        collection: colección de Chroma ya abierta.
    """

    def __init__(self, client, collection):
        self.client = client
        self.collection = collection

    def ingest_document(self, doc_id, text, source):
        """Chunkea, embebe y persiste un documento; devuelve cuántos chunks guardó.

        Usa `upsert` con ids derivados de `doc_id` para que re-ingestar el mismo
        documento reemplace sus chunks en vez de duplicarlos.
        """
        chunks = chunk_text(text)
        if not chunks:
            return 0
        embeddings = embed_texts(self.client, chunks)
        self.collection.upsert(
            ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{"source": source} for _ in chunks],
        )
        return len(chunks)

    def query(self, text, k=4):
        """Recupera los `k` chunks más similares a `text`, con su fuente.

        Returns:
            list[dict]: cada hit con `text`, `source` y `distance` (menor = más
            parecido). Lista vacía si el índice todavía no tiene documentos.
        """
        embedding = embed_texts(self.client, [text])[0]
        result = self.collection.query(query_embeddings=[embedding], n_results=k)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            {
                "text": document,
                "source": (metadata or {}).get("source", "desconocida"),
                "distance": distance,
            }
            for document, metadata, distance in zip(documents, metadatas, distances)
        ]

    def count(self):
        """Cantidad de chunks indexados (útil para verificar la ingesta)."""
        return self.collection.count()


def make_rag_store(client, persist_dir=DEFAULT_PERSIST_DIR, collection_name=COLLECTION_NAME):
    """Arma el `RagStore` sobre una colección persistente de Chroma.

    Devuelve None si `chromadb` no está instalado, para que la tool `retrieve`
    degrade a un stub sin romper el arranque del agente.
    """
    try:
        import chromadb
    except ImportError:
        return None
    chroma = chromadb.PersistentClient(path=persist_dir)
    collection = chroma.get_or_create_collection(name=collection_name)
    return RagStore(client, collection)
