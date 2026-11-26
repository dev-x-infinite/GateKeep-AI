import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.chunker import TextChunk

# Initialize ChromaDB persistent client pointing to our local folder
chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIR,
    settings=ChromaSettings(anonymized_telemetry=False),
)

COLLECTION_NAME = "production_rag_collection"

# Get or create the unified collection with cosine similarity
rag_collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def add_chunks_to_vector_db(
    chunks: list[TextChunk],
    embeddings: list[list[float]],
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
) -> None:
    """
    Inserts chunks, precomputed embeddings, and structured metadata into ChromaDB.
    """
    if not chunks:
        return

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        # Unique ID per chunk
        ids.append(f"{document_id}_{chunk.chunk_index}")
        documents.append(chunk.text)
        metadatas.append(
            {
                "user_id": str(user_id),
                "document_id": str(document_id),
                "filename": filename,
                "page": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            }
        )

    rag_collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def delete_document_from_vector_db(document_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """
    Deletes all vector embeddings belonging to a document,
    filtered by user_id to ensure tenant isolation.
    """
    rag_collection.delete(
        where={
            "$and": [
                {"document_id": {"$eq": str(document_id)}},
                {"user_id": {"$eq": str(user_id)}},
            ]
        }
    )


def query_vector_db(
    query_embedding: list[float],
    user_id: uuid.UUID,
    top_k: int = 5,
) -> list[dict]:
    """
    Searches ChromaDB for the closest chunks to the query vector,
    strictly filtered to only retrieve chunks belonging to the requesting user.
    """
    total_count = rag_collection.count()
    if total_count == 0:
        return []

    # Ensure we don't request more results than exist in the collection
    n_results = min(top_k, total_count)

    results = rag_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"user_id": {"$eq": str(user_id)}},
    )

    extracted_results: list[dict] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for doc_text, metadata in zip(documents, metadatas):
        extracted_results.append(
            {
                "text": doc_text,
                "filename": metadata.get("filename", "unknown"),
                "page": metadata.get("page", 1),
                "chunk_index": metadata.get("chunk_index", 0),
            }
        )

    return extracted_results

