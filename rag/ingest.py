"""Ingesta de documentos al vector store RAG: recorre, lee, chunkea y embebe.

`ingest_path` es la función reusable (la usa quien tenga un `RagStore` armado);
`python -m rag.ingest <ruta>` es el CLI para poblar el índice a mano y verificar
el pipeline end-to-end. Recorre solo archivos de texto conocidos y saltea lo que
no puede leer, sin romper la corrida.
"""

import os
import sys

# Extensiones de texto que tiene sentido indexar (docs y código de un repo).
TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".java", ".go", ".rb",
    ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini", ".sh",
}


def ingest_path(store, path):
    """Ingesta un archivo o un directorio (recursivo) de docs al `store`.

    Args:
        store (RagStore): vector store destino.
        path (str): archivo o carpeta a ingestar.

    Returns:
        tuple[int, int]: (documentos ingestados, chunks totales guardados).
    """
    docs = 0
    total_chunks = 0
    for file_path in _collect_text_files(path):
        text = _read_text(file_path)
        if text is None:
            continue
        chunks = store.ingest_document(file_path, text, file_path)
        if chunks:
            docs += 1
            total_chunks += chunks
    return docs, total_chunks


def _collect_text_files(path):
    """Devuelve los archivos de texto bajo `path` (o `path` si ya es un archivo)."""
    if os.path.isfile(path):
        return [path]
    collected = []
    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in TEXT_EXTENSIONS:
                collected.append(os.path.join(root, name))
    return collected


def _read_text(file_path):
    """Lee un archivo de texto; devuelve None si no se puede (y lo saltea)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def main():
    """CLI: `python -m rag.ingest <ruta>` puebla el índice RAG desde el entorno."""
    if len(sys.argv) != 2:
        print("Uso: python -m rag.ingest <archivo-o-directorio>")
        raise SystemExit(2)

    # Import diferido: el cliente OpenAI (único borde, instrumentado) vive en
    # `agent`, pero el paquete `rag` no depende de `agent` salvo en este CLI.
    from dotenv import load_dotenv

    from agent.llm import build_client
    from .store import make_rag_store

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: falta OPENAI_API_KEY para generar embeddings.")
        raise SystemExit(1)

    store = make_rag_store(build_client(api_key))
    if store is None:
        print("Error: RAG no disponible (¿falta instalar chromadb?).")
        raise SystemExit(1)

    try:
        docs, chunks = ingest_path(store, sys.argv[1])
    except Exception as e:  # noqa: BLE001
        print(f"Error: falló la ingesta RAG: {e}")
        raise SystemExit(1) from None
    print(f"Ingesta completa: {docs} documento(s), {chunks} chunk(s). "
          f"Total en el índice: {store.count()}.")


if __name__ == "__main__":
    main()
