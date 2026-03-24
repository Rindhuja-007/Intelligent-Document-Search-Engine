from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import sqlite3
import pickle
from sentence_transformers import SentenceTransformer
from backend.auth import (
    hash_password,
    verify_password,
    create_token,
    decode_token
)

from database import fetch_all_chunks, create_tables, document_exists, insert_query
from search_engine import retrieve_top_chunks_with_scores
from rag_engine import build_extractive_answer
import os
import shutil
from threading import Lock
from fastapi import UploadFile, File
from document_loader import extract_pdf_chunks, extract_docx_chunks
from preprocessing import preprocess_text
from vectorizer import embed_chunks
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

DB_PATH = os.getenv("DB_NAME", "documents.db")
DATA_DIR = os.getenv("DATA_DIR", "data")

frontend_url = os.getenv("FRONTEND_URL")
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")

allowed_origins = [
    origin.strip()
    for origin in allowed_origins_env.split(",")
    if origin.strip()
]

if frontend_url:
    allowed_origins.append(frontend_url)

# Local dev fallback
if not allowed_origins:
    allowed_origins = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
create_tables()


def ensure_admin_user():
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE username=?",
        (admin_username,)
    )
    existing = cursor.fetchone()

    if not existing:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (admin_username, hash_password(admin_password), "admin")
        )
        conn.commit()

    conn.close()


ensure_admin_user()


# -----------------------------
# Load embedding model
# -----------------------------
model = None
model_lock = Lock()
upload_lock = Lock()


def load_model():
    global model

    if model is None:
        with model_lock:
            if model is None:
                print("Loading model...")
                model = SentenceTransformer(
                    os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
                )
                print("Model loaded.")

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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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
    load_model()

    try:

        chunks, embeddings = fetch_all_chunks()

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

    if not upload_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Another upload is in progress. Please wait.")

    load_model()

    upload_dir = os.path.join(DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    # 1️⃣ Save file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2️⃣ Check if already indexed
    if document_exists(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Document already uploaded"
        )

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cursor = conn.cursor()

    try:
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

        max_chunks_per_upload = int(os.getenv("MAX_CHUNKS_PER_UPLOAD", "150"))
        if len(doc_chunks) > max_chunks_per_upload:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Document too large for current plan. "
                    f"Max chunks per upload: {max_chunks_per_upload}. "
                    f"Current chunks: {len(doc_chunks)}"
                )
            )

        # 5️⃣ Save document metadata
        cursor.execute(
            "INSERT INTO documents (filename, uploaded_by) VALUES (?, ?)",
            (file.filename, user["username"])
        )
        conn.commit()

        # 6️⃣ Create embeddings and insert in small batches
        embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "4"))
        total_indexed = 0

        for start in range(0, len(doc_chunks), embed_batch_size):
            batch = doc_chunks[start:start + embed_batch_size]
            texts = [c["clean_text"] for c in batch]

            batch_embeddings = model.encode(
                texts,
                batch_size=embed_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            rows = [
                (
                    c["filename"],
                    c["page"],
                    c["chunk_id"],
                    c["content"],
                    pickle.dumps(e),
                )
                for c, e in zip(batch, batch_embeddings)
            ]

            cursor.executemany(
                """
                INSERT INTO document_chunks
                (filename, page, chunk_id, content, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            total_indexed += len(batch)

        return {
            "message": "Document uploaded and indexed",
            "chunks_indexed": total_indexed
        }

    except HTTPException:
        cursor.execute("DELETE FROM document_chunks WHERE filename=?", (file.filename,))
        cursor.execute("DELETE FROM documents WHERE filename=?", (file.filename,))
        conn.commit()
        raise
    except sqlite3.IntegrityError:
        conn.rollback()
        cursor.execute("DELETE FROM document_chunks WHERE filename=?", (file.filename,))
        cursor.execute("DELETE FROM documents WHERE filename=?", (file.filename,))
        conn.commit()
        raise HTTPException(status_code=400, detail="Document already uploaded")
    except sqlite3.OperationalError:
        conn.rollback()
        cursor.execute("DELETE FROM document_chunks WHERE filename=?", (file.filename,))
        cursor.execute("DELETE FROM documents WHERE filename=?", (file.filename,))
        conn.commit()
        raise HTTPException(status_code=503, detail="Database busy. Please retry.")
    except Exception:
        conn.rollback()
        cursor.execute("DELETE FROM document_chunks WHERE filename=?", (file.filename,))
        cursor.execute("DELETE FROM documents WHERE filename=?", (file.filename,))
        conn.commit()
        raise HTTPException(status_code=500, detail="Upload failed. Please retry.")
    finally:
        conn.close()
        upload_lock.release()

@app.get("/admin/users")
def list_users(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, role FROM users")

    users = cursor.fetchall()

    conn.close()

    return {"users": users}

@app.get("/documents")
def list_documents(user = Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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