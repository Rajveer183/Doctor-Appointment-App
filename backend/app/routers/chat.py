from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.chat import run_chat

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    history = [{"role": m.role, "content": m.content} for m in payload.conversation_history]
    result = await run_chat(db, payload.patient_id, payload.message, history)
    return ChatResponse(
        reply=result.reply,
        tool_events=[{"tool": e.tool, "arguments": e.arguments, "result": e.result} for e in result.tool_events],
    )
