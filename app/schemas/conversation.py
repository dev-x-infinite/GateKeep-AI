import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.conversation import MessageRole


class MessageResponse(BaseModel):
    """Public representation of a single chat message."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    sources: list[dict[str, Any]] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Payload to start a new conversation thread."""
    title: str | None = Field(None, max_length=255, description="Optional custom conversation title")


class ConversationResponse(BaseModel):
    """Summary representation of a conversation (used in list views)."""
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Detailed representation of a conversation including its full message history."""
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    """Request payload when sending a new message in a conversation thread."""
    content: str = Field(..., min_length=1, max_length=4000, description="The message/question text")


class ChatResponse(BaseModel):
    """Response returned after processing a conversational RAG turn."""
    user_message: MessageResponse
    assistant_message: MessageResponse

