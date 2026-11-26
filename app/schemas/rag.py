from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    """Represents a retrieved chunk cited in the answer."""
    filename: str
    page: int
    text: str
    chunk_index: int


class QueryRequest(BaseModel):
    """Request payload for asking a question."""
    question: str = Field(..., min_length=2, max_length=2000, description="The user's question")
    top_k: int = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")


class QueryResponse(BaseModel):
    """Response returned by the RAG pipeline."""
    answer: str
    sources: list[SourceItem]
