"""Embeddings OpenAI para el pipeline RAG (`text-embedding-3-small`).

Reusa el cliente OpenAI compartido: si vino instrumentado con Langfuse
(`build_openai_client`), cada llamada a `embeddings.create` también queda trazada
sin agregar un segundo borde con OpenAI.
"""

EMBEDDING_MODEL = "text-embedding-3-small"


def embed_texts(client, texts):
    """Genera embeddings para una lista de textos con `text-embedding-3-small`.

    Args:
        client: cliente OpenAI compartido.
        texts (list[str]): textos a embeber (chunks o una consulta).

    Returns:
        list[list[float]]: un vector de embedding por texto, en el mismo orden.
    """
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
