# Intelligent Document Search

An AI-powered document search and retrieval system that uses Retrieval-Augmented Generation (RAG) to answer questions based on uploaded documents. Built with Streamlit, embeddings, and local LLMs via Ollama.

## Overview

This application enables users to:
- Upload and process multiple documents (PDF, DOCX, TXT)
- Ask natural language questions about the documents
- Receive intelligent, context-aware answers powered by AI
- View search history and query results with source citations
- Experience fast semantic search using embeddings

## Features

- **📄 Multi-Format Document Support**: Process PDF, DOCX, and TXT files
- **🔍 Semantic Search**: Uses embeddings and cosine similarity for intelligent retrieval
- **🤖 RAG Pipeline**: Retrieval-Augmented Generation for accurate answers
- **💾 SQLite Database**: Persistent storage of documents, chunks, and query history
- **🎯 Question Type Detection**: Automatically detects question types (definition, importance, types, general)
- **📊 Source Attribution**: Shows source document and page information with answers
- **🌐 Streamlit UI**: Interactive web interface for easy interaction
- **⚡ Local LLM Integration**: Uses Ollama for local LLM inference (no API fees)

## Architecture

### Core Components

| Component | Purpose |
|-----------|---------|
| **app.py** | Streamlit UI and main application entry point |
| **document_loader.py** | Extracts and chunks documents from various formats |
| **preprocessing.py** | Text cleaning and preprocessing utilities |
| **vectorizer.py** | Converts text to embeddings using Sentence Transformers |
| **search_engine.py** | Retrieves relevant chunks using semantic similarity |
| **rag_engine.py** | Builds prompts and generates answers via LLM |
| **database.py** | SQLite database management |

### Data Flow

```
User Input (Question)
    ↓
Query Normalization & Type Detection
    ↓
Vectorization (Sentence Transformers)
    ↓
Semantic Search (Cosine Similarity)
    ↓
Top-K Chunk Retrieval
    ↓
RAG Prompt Construction
    ↓
LLM Inference (Ollama)
    ↓
Answer Generation with Source Citations
    ↓
Query History Storage
```

## Installation

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running (for local LLM)
- pip package manager

### Setup Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd intelligent_document_search
   ```

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure Ollama is running**
   ```bash
   ollama serve
   ```
   
   In another terminal, pull a model:
   ```bash
   ollama pull llama3
   ```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Deploy on Render

This repo includes [render.yaml](render.yaml) so you can deploy both API and frontend using a Blueprint.

### 1) Push code to GitHub
- Commit your latest code
- Push to a GitHub repository

### 2) Create Blueprint on Render
- In Render dashboard: **New +** → **Blueprint**
- Select your GitHub repo
- Render reads [render.yaml](render.yaml) and creates:
    - `ai-doc-assistant-api` (FastAPI web service)
    - `ai-doc-assistant-web` (static frontend)

### 3) Set required environment values
In API service environment:
- `ADMIN_USERNAME` = your admin username
- `ADMIN_PASSWORD` = your admin password

Other variables are preconfigured in [render.yaml](render.yaml):
- `DB_NAME=/var/data/documents.db`
- `DATA_DIR=/var/data`
- `JWT_SECRET_KEY` (auto-generated)

### 4) Deploy
- Click **Apply** in Blueprint setup
- Wait for both services to finish deploying

### 5) Verify
- Open API URL and check root endpoint returns:
    - `{"message": "AI Document Search API running"}`
- Open frontend URL, login with admin credentials from step 3

### Notes
- Persistent disk is configured at `/var/data` for SQLite + uploads.
- First request that uses embeddings may be slower while model files are downloaded.

### How to Use

1. **Upload Documents**
   - Click the file uploader in the sidebar
   - Select PDF, DOCX, or TXT files
   - Click "Process Documents" to index them

2. **Ask Questions**
   - Enter your question in the search box
   - The system will retrieve relevant document chunks
   - An answer will be generated using the local LLM

3. **View Results**
   - See the generated answer with source citations
   - View relevance scores for retrieved chunks
   - Check query history for previous searches

4. **Manage Data**
   - View all processed documents in the sidebar
   - Clear query history as needed
   - Documents are stored in `data/documents/`

## Project Structure

```
intelligent_document_search/
├── app.py                    # Main Streamlit application
├── database.py               # SQLite database operations
├── document_loader.py        # Document parsing & chunking
├── preprocessing.py          # Text preprocessing utilities
├── rag_engine.py             # RAG pipeline & LLM integration
├── search_engine.py          # Semantic search with embeddings
├── vectorizer.py             # Text-to-embedding conversion
├── test.py                   # Testing utilities
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── data/
    ├── documents/            # Uploaded documents
    └── uploads/              # Temporary upload storage
```

## Dependencies

| Package | Purpose |
|---------|---------|
| **streamlit** | Web UI framework |
| **sentence-transformers** | Embeddings generation |
| **scikit-learn** | Cosine similarity calculations |
| **PyPDF2** | PDF document parsing |
| **python-docx** | DOCX document parsing |
| **nltk** | Natural language processing |
| **spacy** | Advanced NLP (optional) |
| **pdfplumber** | PDF text extraction |
| **numpy** | Numerical computations |
| **sqlite3** | Database (built-in) |

## Configuration

### Model Settings

Edit these variables in the code to customize:

```python
# Embedding Model (in app.py or vectorizer.py)
model = SentenceTransformer("all-MiniLM-L6-v2")

# LLM Model (in rag_engine.py)
model = "llama3"  # Change to other Ollama models like "mistral", "neural-chat"

# Chunk Settings (in document_loader.py)
chunk_size = 500    # Words per chunk
overlap = 50        # Word overlap between chunks

# Search Settings (in search_engine.py)
top_k = 5           # Number of chunks to retrieve
```

### Ollama Models

Available models you can use:

```bash
ollama pull llama3           # Fast, good quality
ollama pull mistral          # Larger, more accurate
ollama pull neural-chat      # Conversational
ollama pull openhermes       # Creative writing
```

## Database Schema

The SQLite database includes:

- **documents**: Stores uploaded documents metadata
- **chunks**: Stores document chunks with embeddings
- **queries**: Stores query history with responses

## API Reference

### Key Functions

```python
# Document Processing
extract_pdf_chunks(file_path) -> list
extract_docx_chunks(file_path) -> list
chunk_text(text, chunk_size, overlap) -> list

# Vectorization
generate_embeddings(text_chunks) -> np.array

# Search
retrieve_top_chunks_with_scores(query_embedding, chunks, embeddings, top_k)

# RAG
build_prompt(question, contexts) -> str
ask_llm(prompt, model) -> str

# Database
create_tables()
insert_chunk(document_id, chunk_index, content, embedding)
fetch_all_chunks()
insert_query(question, answer, source_docs)
```

## Performance Tips

1. **Use smaller models for faster responses**: `ollama pull neural-chat`
2. **Increase chunk size for better context**: `chunk_size = 1000`
3. **Reduce top_k for faster search**: `top_k = 3`
4. **Preprocess large documents** before uploading
5. **Run on GPU** for 5-10x faster embeddings

## Troubleshooting

### Issue: "Ollama connection refused"
**Solution**: Make sure Ollama is running (`ollama serve`)

### Issue: Slow response times
**Solution**: 
- Use a smaller model
- Increase chunk size
- Reduce number of retrieved chunks (top_k)

### Issue: Out of memory
**Solution**:
- Process fewer documents at once
- Reduce chunk size
- Use a smaller embedding model

### Issue: Inaccurate answers
**Solution**:
- Check if documents are properly indexed
- Try a larger LLM model
- Ensure question matches document content

## Limitations

- Requires Ollama and models to be downloaded locally (~7-40GB depending on model)
- Response time depends on local hardware
- Limited to documents uploaded by user
- No multi-user support (local deployment)

## Future Enhancements

- [ ] Support for web scraping and URL indexing
- [ ] Vector database (Pinecone, Weaviate) for scalability
- [ ] Multi-turn conversations with memory
- [ ] User authentication and multi-user support
- [ ] Response caching for identical queries
- [ ] Advanced filters (date, document type, etc.)
- [ ] Export results to PDF/CSV
- [ ] Batch processing for large document sets

## Contributing

Contributions are welcome! Areas for improvement:
- Better preprocessing and cleaning
- Additional document format support
- Performance optimizations
- UI/UX improvements
- Test coverage

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or suggestions:
1. Check the troubleshooting section
2. Review Ollama documentation
3. Check Streamlit documentation
4. Open an issue in the repository

## Acknowledgments

- [Streamlit](https://streamlit.io/) - Web framework
- [Sentence Transformers](https://www.sbert.net/) - Embeddings
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [scikit-learn](https://scikit-learn.org/) - ML utilities

---

**Last Updated**: February 2026  
**Version**: 1.0.0
