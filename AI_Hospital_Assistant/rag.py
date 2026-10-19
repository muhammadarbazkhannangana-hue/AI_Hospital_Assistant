import os
import fitz
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def get_pdf_status(pdf_path):
    if os.path.exists(pdf_path):
        return f"PDF ready: {pdf_path}"
    return f"PDF not found yet: {pdf_path}. You can upload one above."

def _extract_text(pdf_path):
    if not os.path.exists(pdf_path):
        return ""
    with fitz.open(pdf_path) as doc:
        return "\n".join(page.get_text("text") for page in doc)

def _chunks(text, chunk_size=850, overlap=120):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks

def answer_from_pdf(pdf_path, question, top_k=3):
    text = _extract_text(pdf_path)
    if not text.strip():
        return "PDF_ISSUE:PDF missing, empty, or contains no selectable text. Add a readable PDF in the data folder."
    chunks = _chunks(text)
    if not chunks:
        return "PDF_ISSUE:No readable text was found in the PDF."
    model = _get_model()
    vectors = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
    vectors = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    q_vector = model.encode([question], convert_to_numpy=True, normalize_embeddings=True)
    q_vector = np.asarray(q_vector, dtype="float32")
    _, indices = index.search(q_vector, min(top_k, len(chunks)))
    return "\n\n---\n\n".join(chunks[int(i)] for i in indices[0] if i >= 0)
