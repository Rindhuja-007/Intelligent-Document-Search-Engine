from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import sqlite3
from sentence_transformers import SentenceTransformer
from backend.auth import (
    hash_password,
    verify_password,
    create_token,
    decode_token
)

from database import fetch_all_chunks, create_tables,insert_chunk, document_exists, insert_query
from search_engine import retrieve_top_chunks_with_scores
from rag_engine import build_extractive_answer
import os
from fastapi import UploadFile, File
from document_loader import extract_pdf_chunks, extract_docx_chunks
from preprocessing import preprocess_text
from vectorizer import embed_chunks
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
create_tables()


# -----------------------------
# Load embedding model
# -----------------------------
model = None
chunks = None
embeddings = None


def load_resources():
    global model, chunks, embeddings

    if model is None:
        print("Loading model...")
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            local_files_only=True
        )
        print("Model loaded.")

    if chunks is None or embeddings is None:
        print("Loading DB...")
        chunks, embeddings = fetch_all_chunks()
        print("DB loaded.")

# -----------------------------
# Authentication Dependency
# -----------------------------
def get_current_user(credentials = Depends(security)):

    token = credentials.credentials

    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload


# -----------------------------
# Request Models
# -----------------------------
class Query(BaseModel):
    question: str


class User(BaseModel):
    username: str
    password: str


# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/")
def root():
    return {"message": "AI Document Search API running"}


# -----------------------------
# Register User
# -----------------------------
@app.post("/register")
def register(user: User):

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    hashed = hash_password(user.password)

    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (user.username, hashed, "user")
        )
        conn.commit()

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    finally:
        conn.close()

    return {"message": "User registered successfully"}


# -----------------------------
# Login
# -----------------------------
@app.post("/login")
def login(user: User):

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password, role FROM users WHERE username=?",
        (user.username,)
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    hashed_password, role = result

    if not verify_password(user.password, hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password"
        )

    token = create_token({
        "username": user.username,
        "role": role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role
    }


# -----------------------------
# Query Documents (Protected)
# -----------------------------
@app.post("/query")
def query_docs(data: Query, user=Depends(get_current_user)):
    load_resources()

    try:

        if not chunks:
            return {"error": "No documents indexed"}

        query_embedding = model.encode(data.question)

        ranked_chunks = retrieve_top_chunks_with_scores(
            query_embedding,
            chunks,
            embeddings,
            top_k=5
        )

        answer_points, sources = build_extractive_answer(
            ranked_chunks,
            query_word=data.question.split()[-1],
            question_type="general"
        )

        insert_query(
            user["username"],
            data.question,
            " ".join(answer_points)
        )

        return {
            "user": user["username"],
            "role": user["role"],
            "answer": answer_points,
            "sources": sources
        }

    except Exception as e:
        return {"error": str(e)}

@app.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):

    # Only admin can upload
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    os.makedirs("data/uploads", exist_ok=True)

    file_path = os.path.join("data/uploads", file.filename)

    # 1️⃣ Save file
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # 2️⃣ Check if already indexed
    if document_exists(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Document already uploaded"
        )

    
    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO documents (filename, uploaded_by) VALUES (?, ?)",
        (file.filename, user["username"])
    )

    conn.commit()
    conn.close()
    

    # 3️⃣ Extract chunks
    if file.filename.endswith(".pdf"):
        doc_chunks = extract_pdf_chunks(file_path)
    elif file.filename.endswith(".docx"):
        doc_chunks = extract_docx_chunks(file_path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file")

    # 4️⃣ Preprocess
    for c in doc_chunks:
        c["clean_text"] = preprocess_text(c["content"])

    # 5️⃣ Create embeddings
    embeddings, _ = embed_chunks(doc_chunks)

    # 6️⃣ Store chunks
    for c, e in zip(doc_chunks, embeddings):
        insert_chunk(c, e)

    return {
        "message": "Document uploaded and indexed",
        "chunks_indexed": len(doc_chunks)
    }

@app.get("/admin/users")
def list_users(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, role FROM users")

    users = cursor.fetchall()

    conn.close()

    return {"users": users}

@app.get("/documents")
def list_documents(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename, uploaded_by, uploaded_at
        FROM documents
        ORDER BY uploaded_at DESC
    """)

    docs = cursor.fetchall()

    conn.close()

    return [
        {
            "id": d[0],
            "filename": d[1],
            "uploaded_by": d[2],
            "uploaded_at": d[3]
        }
        for d in docs
    ]

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int, user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    # get filename
    cursor.execute(
        "SELECT filename FROM documents WHERE id=?",
        (doc_id,)
    )

    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = result[0]

    # delete metadata
    cursor.execute(
        "DELETE FROM documents WHERE id=?",
        (doc_id,)
    )

    # delete chunks
    cursor.execute(
        "DELETE FROM document_chunks WHERE filename=?",
        (filename,)
    )

    conn.commit()
    conn.close()

    return {"message": f"{filename} deleted"}

@app.get("/admin/stats")
def admin_stats(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    # documents
    cursor.execute("SELECT COUNT(*) FROM documents")
    documents = cursor.fetchone()[0]

    # chunks
    cursor.execute("SELECT COUNT(*) FROM document_chunks")
    chunks = cursor.fetchone()[0]

    # users
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    # queries
    cursor.execute("SELECT COUNT(*) FROM query_history")
    queries = cursor.fetchone()[0]

    conn.close()

    return {
        "documents": documents,
        "chunks": chunks,
        "users": users,
        "queries": queries
    }

@app.get("/admin/analytics")
def admin_analytics(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()

    # total queries
    cursor.execute("SELECT COUNT(*) FROM query_history")
    total_queries = cursor.fetchone()[0]

    # most searched questions
    cursor.execute("""
        SELECT question, COUNT(*) as count
        FROM query_history
        GROUP BY question
        ORDER BY count DESC
        LIMIT 5
    """)
    top_questions = cursor.fetchall()

    # most active users
    cursor.execute("""
        SELECT username, COUNT(*) as count
        FROM query_history
        GROUP BY username
        ORDER BY count DESC
        LIMIT 5
    """)
    active_users = cursor.fetchall()

    conn.close()

    return {
        "total_queries": total_queries,
        "top_questions": [
            {"question": q[0], "count": q[1]} for q in top_questions
        ],
        "active_users": [
            {"username": u[0], "count": u[1]} for u in active_users
        ]
    }