"""Pipeline RAG: ingesta de docs -> chunking -> embeddings OpenAI -> Chroma.

Vive fuera del paquete `agent/` (como `repo.py`) porque es infraestructura de
recuperación que el agente *usa* a través de la tool `retrieve`, no una pieza del
loop del `Harness`. El corte: `make_rag_store` arma el vector store sobre Chroma,
`ingest_path` lo puebla con documentos y `RagStore.query` recupera chunks con sus
fuentes. Degrada con elegancia (igual que `web_search` sin `TAVILY_API_KEY`): si
`chromadb` no está instalado, `make_rag_store` devuelve None y la tool `retrieve`
se vuelve un stub que avisa que el RAG no está disponible.
"""

from .ingest import ingest_path
from .store import RagStore, make_rag_store

__all__ = ["RagStore", "make_rag_store", "ingest_path"]
