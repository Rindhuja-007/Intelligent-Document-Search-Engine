import sqlite3
import numpy as np
import pickle
import os

DB_NAME = os.getenv("DB_NAME", "documents.db")


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            page INTEGER,
            chunk_id INTEGER,
            content TEXT,
            embedding BLOB
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            question TEXT,
            answer TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            uploaded_by TEXT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)


    conn.commit()
    conn.close()


def insert_chunk(chunk, embedding):
    conn = get_connection()
    cursor = conn.cursor()

    embedding_blob = pickle.dumps(embedding)

    cursor.execute("""
        INSERT INTO document_chunks
        (filename, page, chunk_id, content, embedding)
        VALUES (?, ?, ?, ?, ?)
    """, (
        chunk["filename"],
        chunk["page"],
        chunk["chunk_id"],
        chunk["content"],
        embedding_blob
    ))

    conn.commit()
    conn.close()


def fetch_all_chunks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename, page, chunk_id, content, embedding
        FROM document_chunks
    """)

    rows = cursor.fetchall()
    conn.close()

    chunks = []
    embeddings = []

    for row in rows:
        chunks.append({
            "filename": row[0],
            "page": row[1],
            "chunk_id": row[2],
            "content": row[3]
        })
        embeddings.append(pickle.loads(row[4]))

    return chunks, np.array(embeddings)

def document_exists(filename):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM document_chunks WHERE filename = ?",
        (filename,)
    )

    exists = cursor.fetchone()[0] > 0
    conn.close()

    return exists

def insert_query(username, question, answer):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO query_history (username, question, answer) VALUES (?, ?, ?)",
        (username, question, answer[:500])
    )

    conn.commit()
    conn.close()

def fetch_query_history(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT question, answer, timestamp
        FROM query_history
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_query_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM query_history")

    conn.commit()
    conn.close()

