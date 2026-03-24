from sentence_transformers import SentenceTransformer


_embedding_model = None


def get_embedding_model(model_name="all-MiniLM-L6-v2"):
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(model_name)

    return _embedding_model


def embed_chunks(chunks, model=None):
    if model is None:
        model = get_embedding_model()

    texts = [chunk["clean_text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    return embeddings, model
