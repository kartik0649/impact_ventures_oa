import os
import uuid
import shutil
import logging

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------------
# Important: pip install langchain faiss-cpu pdfplumber fastapi uvicorn python-multipart
# -------------------------------------------------------------------

# 1) For embeddings:
from langchain.embeddings import HuggingFaceEmbeddings
# or:
# from langchain.embeddings import OpenAIEmbeddings
# (if using OpenAI, pip install openai and set OPENAI_API_KEY)

# 2) For text splitting / doc store:
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

# 3) FAISS Vector Store from LangChain:
from langchain.vectorstores import FAISS

app = FastAPI()

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global config
embedding_function = HuggingFaceEmbeddings()  # or OpenAIEmbeddings(openai_api_key=...)
faiss_store = None  # We'll store our in-memory FAISS index here.


@app.on_event("startup")
def startup_event():
    """
    Runs when FastAPI starts. Initialize your FAISS store if needed.
    """
    global faiss_store
    # Initially, there's no data, so we set it to None or an empty store.
    faiss_store = None
    logging.info("FAISS vector store is ready to ingest data.")


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    logging.info("Upload PDF endpoint hit: %s", file.filename)
    """
    Upload and ingest a PDF. We'll:
      1. Save the file temporarily
      2. Extract text + table data
      3. Chunk the text
      4. Embed + store in FAISS
    """
    global faiss_store

    # Save to temp
    file_id = str(uuid.uuid4())
    temp_file_path = f"./tp_{file.filename}"
    with open(temp_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    pdf_text = extract_text_and_tables(temp_file_path)

    # Chunk the text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = text_splitter.split_text(pdf_text)

    # Create Document list
    docs = [Document(page_content=c, metadata={"source": file.filename}) for c in chunks]

    # If we haven't created the store yet, create it from scratch;
    # otherwise, add to existing.
    if faiss_store is None:
        faiss_store = FAISS.from_documents(docs, embedding_function)
    else:
        faiss_store.add_documents(docs)

    # Clean up
    os.remove(temp_file_path)

    return JSONResponse({"status": "success", "message": "PDF ingested successfully."})


@app.post("/query")
async def query_documents(query: str = Form(...), top_k: int = Form(5)):
    """
    Query the in-memory FAISS index for matching chunks.
    Return top_k results.
    """
    global faiss_store
    if faiss_store is None:
        return JSONResponse({"error": "No documents are ingested yet."}, status_code=400)

    results = faiss_store.similarity_search(query, k=top_k)
    # Return the chunk content + metadata
    matches = []
    for i, doc in enumerate(results):
        matches.append({
            "rank": i + 1,
            "source": doc.metadata.get("source", "N/A"),
            "content": doc.page_content
        })

    return {"query": query, "results": matches}


def extract_text_and_tables(pdf_path: str) -> str:
    """
    Extract text and tables from a PDF using pdfplumber.
    Tables are converted to CSV-like rows and appended.
    """
    extracted_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            extracted_text.append(page_text)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    row_text = ", ".join(str(cell) for cell in row)
                    extracted_text.append(row_text)

    return "\n".join(extracted_text)
