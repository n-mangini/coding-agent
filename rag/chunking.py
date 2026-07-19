"""Chunking de documentos para el pipeline RAG.

Partimos por caracteres con solapamiento: es simple, estable y suficiente para
docs de repos (código y markdown). El solapamiento evita cortar una idea justo en
el límite de un chunk y perder contexto entre uno y el siguiente.
"""


def chunk_text(text, chunk_size=1000, overlap=200):
    """Parte `text` en ventanas de hasta `chunk_size` caracteres solapadas.

    Args:
        text (str): el documento a chunkear.
        chunk_size (int): tamaño máximo de cada chunk en caracteres.
        overlap (int): caracteres compartidos entre chunks consecutivos.

    Returns:
        list[str]: los chunks no vacíos, en orden.
    """
    if not text or not text.strip():
        return []

    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        # El último chunk ya cubre hasta el final: cortamos para no repetirlo.
        if start + chunk_size >= len(text):
            break
    return chunks
