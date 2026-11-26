import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Public representation of a Document metadata record."""
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
