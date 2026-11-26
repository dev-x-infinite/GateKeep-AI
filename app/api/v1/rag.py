from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db.chroma import query_vector_db
from app.models.user import User
from app.schemas.rag import QueryRequest, QueryResponse, SourceItem
from app.services.gemini import embed_query, generate_rag_answer

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def ask_question(
    query_in: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    RAG Query Endpoint:
    1. Embeds the user's question using Gemini RETRIEVAL_QUERY task type.
    2. Retrieves the most relevant chunks from ChromaDB scoped strictly to the current user.
    3. Synthesizes an answer using Gemini Flash grounded in the retrieved chunks.
    4. Returns the answer along with explicit source citations (filename, page).
    """
    try:
        # 1. Compute 768-dim embedding for the user's query
        query_embedding = embed_query(query_in.question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to embed query: {str(e)}",
        )

    # 2. Retrieve top_k chunks from ChromaDB filtered by user_id
    try:
        context_chunks = query_vector_db(
            query_embedding=query_embedding,
            user_id=current_user.id,
            top_k=query_in.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}",
        )

    # If no documents or chunks exist for this user
    if not context_chunks:
        return QueryResponse(
            answer=(
                "I could not find any relevant documents in your library. "
                "Please upload relevant PDF or TXT files first."
            ),
            sources=[],
        )

    # 3. Generate grounded answer using Gemini Flash
    try:
        answer = generate_rag_answer(
            question=query_in.question,
            context_chunks=context_chunks,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer from LLM: {str(e)}",
        )

    # 4. Build response with sources
    sources = [
        SourceItem(
            filename=c["filename"],
            page=c["page"],
            text=c["text"],
            chunk_index=c["chunk_index"],
        )
        for c in context_chunks
    ]

    return QueryResponse(answer=answer, sources=sources)
