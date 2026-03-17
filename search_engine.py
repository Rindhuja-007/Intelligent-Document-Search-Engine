import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def search_chunks_embedding(query, chunks, embeddings, model, top_k=5):
    query_embedding = model.encode([query], convert_to_numpy=True)

    scores = cosine_similarity(query_embedding, embeddings)[0]

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]

def retrieve_top_chunks_with_scores(query_embedding, chunks, embeddings, top_k=5):
    scores = cosine_similarity([query_embedding], embeddings)[0]

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]
