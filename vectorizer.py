from sentence_transformers import SentenceTransformer


def embed_chunks(chunks):
    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [chunk["clean_text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    return embeddings, model
