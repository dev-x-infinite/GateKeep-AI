import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.chroma import query_vector_db
from app.db.session import get_db
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.gemini import embed_query, generate_conversational_rag_answer

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_in: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new conversation thread for the current user.
    """
    title = conv_in.title.strip() if conv_in.title and conv_in.title.strip() else "New Conversation"

    conversation = Conversation(
        user_id=current_user.id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationResponse], status_code=status.HTTP_200_OK)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all conversation threads belonging to the current user,
    ordered by most recently active first.
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return conversations


@router.get("/{conversation_id}", response_model=ConversationDetailResponse, status_code=status.HTTP_200_OK)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific conversation along with its complete, chronological message history.
    """
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a conversation thread.
    Database foreign key cascading will automatically purge all associated messages.
    """
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    db.delete(conversation)
    db.commit()

    return {"detail": f"Conversation '{conversation.title}' and all its messages were successfully deleted."}


@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def send_message(
    conversation_id: uuid.UUID,
    chat_in: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message within an existing conversation thread:
    1. Loads previous conversation history for conversational context.
    2. Embeds the current question and retrieves relevant document chunks from ChromaDB.
    3. Persists the user's message in the database.
    4. Prompts Gemini Flash with both conversation history and retrieved citations.
    5. Persists the assistant's response along with citations in the database.
    6. Automatically updates the conversation title if it is new.
    """
    # 1. Fetch conversation ensuring it belongs to current_user
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    # 2. Extract recent conversation history for memory (last 8 messages)
    history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in conversation.messages[-8:]
    ]

    # 3. Retrieve relevant document chunks from ChromaDB (user-scoped)
    try:
        query_embedding = embed_query(chat_in.content)
        context_chunks = query_vector_db(
            query_embedding=query_embedding,
            user_id=current_user.id,
            top_k=5,
        )
    except Exception as e:
        context_chunks = []

    # 4. Save user message to database
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=chat_in.content,
    )
    db.add(user_msg)

    # 5. Generate conversational RAG answer using Gemini Flash
    try:
        answer = generate_conversational_rag_answer(
            question=chat_in.content,
            context_chunks=context_chunks,
            chat_history=history,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer from LLM: {str(e)}",
        )

    # 6. Save assistant message with citation metadata
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        sources=context_chunks if context_chunks else None,
    )
    db.add(assistant_msg)

    # 7. Auto-title conversation on first message if still default
    if conversation.title == "New Conversation":
        cleaned_first_turn = chat_in.content.strip().split("\n")[0]
        conversation.title = cleaned_first_turn[:50]

    # 8. Bump updated_at timestamp
    conversation.updated_at = func.now()

    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return ChatResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
    )

