import streamlit as st
import re
from sentence_transformers import SentenceTransformer

from rag_engine import (
    summarize_chunks,
    get_confidence_label,
    build_extractive_answer,
    build_fallback_answer,
)

# =======================
# Helper: Query normalization
# =======================
def normalize_query(q):
    q = q.lower()
    q = re.sub(r"[^\w\s]", "", q)
    return q.strip()


def detect_question_type(q):
    q = q.lower().strip()

    if q.startswith("what is") or q.startswith("define"):
        return "definition"
    if "importance" in q or "advantages" in q:
        return "importance"
    if "types" in q:
        return "types"

    return "general"

def extract_keyword(query):
    stopwords = {
        "what","is","the","a","an","in","of","for",
        "define","explain","about","tell","me"
    }

    words = query.lower().split()

    keywords = [w for w in words if w not in stopwords]

    return keywords[-1] if keywords else words[-1]

# =======================
# Database imports
# =======================
from database import (
    create_tables,
    fetch_all_chunks,
    fetch_query_history,
    insert_query,
    clear_query_history,
    insert_chunk,
    document_exists,
)

# =======================
# Search import
# =======================
from search_engine import retrieve_top_chunks_with_scores


# =======================
# Streamlit config
# =======================
st.set_page_config(
    page_title="AI Document Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =======================
# DB init
# =======================
create_tables()

# =======================
# Sidebar – Query History
# =======================
with st.sidebar:
    st.subheader("Query History")

    if st.button("Clear History"):
        clear_query_history()
        st.success("Query history cleared.")
        st.rerun()

    history = fetch_query_history()

    if not history:
        st.caption("No queries yet.")
    else:
        for q, a, t in history:
            with st.expander(q):
                st.write(a)
                st.caption(t)


# =======================
# Main UI
# =======================
st.title("Document Assistant")
st.caption("Document-grounded answer retrieval using RAG")


# =======================
# Upload Section
# =======================
st.subheader("Upload Document")

uploaded_file = st.file_uploader(
    "Upload a PDF or DOCX",
    type=["pdf", "docx"],
)

if uploaded_file:
    import os
    from document_loader import extract_pdf_chunks, extract_docx_chunks
    from preprocessing import preprocess_text
    from vectorizer import embed_chunks

    os.makedirs("data/uploads", exist_ok=True)
    file_path = os.path.join("data/uploads", uploaded_file.name)

    if document_exists(uploaded_file.name):
        st.warning("This document is already indexed.")
    else:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        st.info("Processing document...")

        if uploaded_file.name.endswith(".pdf"):
            doc_chunks = extract_pdf_chunks(file_path)
        else:
            doc_chunks = extract_docx_chunks(file_path)

        for c in doc_chunks:
            c["clean_text"] = preprocess_text(c["content"])

        embeddings, _ = embed_chunks(doc_chunks)

        for c, e in zip(doc_chunks, embeddings):
            insert_chunk(c, e)

        st.success("Document indexed successfully.")
        st.rerun()


# =======================
# Load Model & Data
# =======================
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


model = load_model()
chunks, embeddings = fetch_all_chunks()


# =======================
# Chat Memory
# =======================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# =======================
# Chat Input
# =======================
question = st.chat_input("Ask a question from the documents")

if question:
    question = question.strip()
    question_type = detect_question_type(question)
    normalized_question = normalize_query(question)

    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            if not chunks:
                answer_text = "No documents are indexed yet."
                st.warning(answer_text)

            else:
                query_embedding = model.encode(normalized_question)

                ranked_chunks = retrieve_top_chunks_with_scores(
                    query_embedding,
                    chunks,
                    embeddings,
                    top_k=5,
                )

                max_score = ranked_chunks[0][1] if ranked_chunks else 0.0
                st.caption(f"Top Match Score: {round(max_score*100,1)}%")
                FOUND_THRESHOLD = 0.25

                st.markdown("### Answer")

                # =======================
                # FOUND
                # =======================
                if max_score >= FOUND_THRESHOLD:

                    core_word = extract_keyword(normalized_question)

                    answer_points, page_info = build_extractive_answer(
                        ranked_chunks,
                        query_word=core_word,
                        question_type=question_type,
                    )

                    if answer_points:

                        # Definition → show single answer
                        if question_type == "definition":
                            st.markdown(answer_points[0])
                            answer_text = answer_points[0]
                        else:
                            for p in answer_points:
                                st.markdown(p)
                            answer_text = "\n".join(answer_points)

                        # =======================
                        # Sources
                        # =======================
                        st.markdown("### Sources")

                        from collections import defaultdict

                        grouped_sources = defaultdict(list)

                        for src in page_info:
                            grouped_sources[src["filename"]].append(src)

                        for filename, items in grouped_sources.items():
                            with st.expander(f"{filename}"):
                                for s in items:

                                    confidence = get_confidence_label(
                                        s["score"] / 100
                                    )

                                    st.write(
                                        f"Page {s['page']} — "
                                        f"{s['score']}% match "
                                        f"({confidence})"
                                    )

                        # =======================
                        # Quick Summary Feature
                        # =======================
                        if st.button("Generate Quick Summary"):
                            summary = summarize_chunks(
                                [c for c, _ in ranked_chunks]
                            )
                            st.subheader("Document Summary")
                            st.write(summary)

                    else:
                        answer_text = build_fallback_answer(question)
                        st.write(answer_text)

                # =======================
                # NOT FOUND
                # =======================
                else:
                    answer_text = build_fallback_answer(question)
                    st.write(answer_text)

                    st.markdown("### Low relevance pages")

                    shown = False
                    for chunk, score in ranked_chunks:
                        if score >= 0.20:
                            st.write(
                                f"Page {chunk['page']} — "
                                f"{round(score * 100,1)}% match"
                            )
                            shown = True

                    if not shown:
                        st.caption("No relevant pages found.")

            insert_query(question, answer_text)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer_text}
    )