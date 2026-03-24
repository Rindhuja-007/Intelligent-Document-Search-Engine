from sentence_transformers import SentenceTransformer
import os


_embedding_model = None


def get_embedding_model(model_name=None):
    global _embedding_model

    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(model_name)

    return _embedding_model


def embed_chunks(chunks, model=None):
    if model is None:
        model = get_embedding_model()

    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "8"))

    texts = [chunk["clean_text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True
    )

    return embeddings, model
