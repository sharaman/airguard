from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

INDEX_DIR = Path(__file__).parent / "faiss_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_vectorstore = None


def _load_index() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        _vectorstore = FAISS.load_local(
            str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True,
        )
    return _vectorstore


def search_rag(query: str, k: int = 3) -> str:
    vs = _load_index()
    docs = vs.similarity_search(query, k=k)
    return "\n\n".join(d.page_content for d in docs)
