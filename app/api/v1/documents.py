import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.chroma import add_chunks_to_vector_db, delete_document_from_vector_db
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.chunker import chunk_pages
from app.services.extractor import extract_text_from_file
from app.services.gemini import embed_texts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF or TXT document, extract text, chunk it,
    compute 768-dim embeddings via Gemini, and store in ChromaDB.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    clean_filename = file.filename.lower()
    if not (clean_filename.endswith(".pdf") or clean_filename.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF and TXT files are accepted.",
        )

    # 1. Read file bytes
    try:
        file_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is completely empty.",
        )

    # 2. Register document in PostgreSQL with status 'processing'
    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        status=DocumentStatus.PROCESSING,
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # 3. Process file: Extract -> Chunk -> Embed -> Index in ChromaDB
    try:
        pages = extract_text_from_file(file_bytes, file.filename)
        chunks = chunk_pages(pages)

        if not chunks:
            raise ValueError("No extractable chunks found in document.")

        chunk_texts = [c.text for c in chunks]
        embeddings = embed_texts(chunk_texts, task_type="RETRIEVAL_DOCUMENT")

        add_chunks_to_vector_db(
            chunks=chunks,
            embeddings=embeddings,
            user_id=current_user.id,
            document_id=document.id,
            filename=file.filename,
        )

        # 4. Update status to 'ready'
        document.status = DocumentStatus.READY
        document.chunk_count = len(chunks)
        db.commit()
        db.refresh(document)
        return document

    except Exception as e:
        logger.error(f"Error processing document {document.id}: {e}", exc_info=True)
        # Mark as failed in DB so the user knows processing failed
        document.status = DocumentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document ingestion failed: {str(e)}",
        )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    filename: str | None = Query(None, description="Optional search term to filter documents by filename"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all documents uploaded by the current user.
    Optionally filter/search by filename substring (case-insensitive).
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)

    if filename:
        query = query.filter(Document.filename.ilike(f"%{filename.strip()}%"))

    # Order most recent first
    documents = query.order_by(Document.created_at.desc()).all()
    return documents


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a document owned by the current user.
    Purges both the PostgreSQL record and all associated vector embeddings in ChromaDB.
    """
    # 1. Fetch document ensuring it belongs to current_user
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to delete it.",
        )

    # 2. Delete vectors from ChromaDB
    try:
        delete_document_from_vector_db(document_id=document.id, user_id=current_user.id)
    except Exception as e:
        logger.warning(f"Could not purge vectors for document {document.id} from ChromaDB: {e}")

    # 3. Delete from PostgreSQL
    db.delete(document)
    db.commit()

    return {"detail": f"Document '{document.filename}' and its vector embeddings were successfully deleted."}

