import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    """Payload for user registration."""
    email: str = Field(..., max_length=255, description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="Plaintext password")


class LoginRequest(BaseModel):
    """Payload for JSON-based login."""
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class Token(BaseModel):
    """Response returned upon successful authentication."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user representation (never exposes password hashes)."""
    id: uuid.UUID
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

