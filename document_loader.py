import os
import PyPDF2
import docx


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap  # overlap for context

    return chunks


def extract_pdf_chunks(file_path):
    documents = []

    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            chunks = chunk_text(text)

            for idx, chunk in enumerate(chunks):
                documents.append({
                    "filename": os.path.basename(file_path),
                    "page": page_number,
                    "chunk_id": idx,
                    "content": chunk
                })

    return documents


def extract_docx_chunks(file_path):
    documents = []
    doc = docx.Document(file_path)

    full_text = " ".join(p.text for p in doc.paragraphs)
    chunks = chunk_text(full_text)

    for idx, chunk in enumerate(chunks):
        documents.append({
            "filename": os.path.basename(file_path),
            "page": None,
            "chunk_id": idx,
            "content": chunk
        })

    return documents


def load_documents(folder_path):
    all_documents = []

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        try:
            if file_name.endswith(".pdf"):
                all_documents.extend(extract_pdf_chunks(file_path))

            elif file_name.endswith(".docx"):
                all_documents.extend(extract_docx_chunks(file_path))

        except Exception as e:
            print(f"[WARNING] Skipping {file_name}: {e}")

    return all_documents
