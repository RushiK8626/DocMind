# MultiModal Document Intelligence Backend

This is the backend for the MultiModal Document Intelligence application. It provides an API for document ingestion, processing (OCR, layout parsing), and conversational intelligence using modern RAG architectures and Agentic AI.

## Tech Stack
- **Web Framework:** Flask
- **Database:** SQLAlchemy
- **Vector Database:** ChromaDB
- **Asynchronous Tasks:** Celery + Redis
- **Authentication:** Flask-JWT-Extended
- **AI/Agents:** LangGraph, LiteLLM
- **Document Parsing:** Docling, pdf2image

## Setup

1. **Clone the repository and install dependencies:**
   Create a virtual environment, then install the dependencies:
   ```bash
   pip install -r requirements.txt
   # OR
   pip install -e .
   ```

2. **Environment Variables:**
   Ensure you have configured all necessary environment variables (e.g., in a `.env` file). You will need keys for your LLM providers, database URLs, Redis configurations, and S3 credentials.
   Check `example.env` for help.

3. **Running the Application:**
   Start the Flask development server:
   ```bash
   flask run
   ```

4. **Running Background Tasks:**
   Start the Celery worker to handle asynchronous document processing:
   ```bash
   celery -A app.tasks.celery_utils.celery worker --loglevel=info --pool=solo
   ```

   If you want concurrency:
   ```bash
   celery -A app.tasks.celery_utils.celery worker --pool=threads --concurrency=4
   ```

5. **Run Chroma Server:**
   Run the Chroma server as its own long-lived process, pointed at the same directory your PersistentClient was already using:
   ```bash
   pip install "chromadb[server]" --break-system-packages
   ```

   ```bash
   chroma run --path /home/rushikesh/MultiModal-Document-Intelligence/backend/chroma_data --port 8000 --host 0.0.0.0
   ```
```
