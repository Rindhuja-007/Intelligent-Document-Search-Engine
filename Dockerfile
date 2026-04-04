FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Hugging Face Spaces requirement for some templates, good practice)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user . $HOME/app

ENV DB_NAME=/tmp/documents.db
ENV DATA_DIR=/tmp

# Start the FastAPI application on port 7860 (default for HF Spaces)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
