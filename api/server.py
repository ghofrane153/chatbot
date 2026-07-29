import os
import sys
import json
import uuid
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent.chatbot_agent import create_chatbot
from guardrails.input_guardrails import check_input
from guardrails.output_guardrails import check_output
from cache.semantic_cache import semantic_cache

load_dotenv()

app = FastAPI(title="Suffelkopie Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://chatbot-ebon-kappa-65.vercel.app",
        "https://chatbot-qmtpxmcmi-a-7740.vercel.app",
        "*"  # ← autorise toutes les origines Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_chatbot()
conversations = {}

LOG_FILE = "logs/chat_logs.json"

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------

def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log(entry: dict):
    logs = load_logs()
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# MODELES
# ---------------------------------------------------------

class MessageRequest(BaseModel):
    message: str
    session_id: str = "default"

class MessageResponse(BaseModel):
    response: str
    message_id: str
    cached: bool = False
    blocked: bool = False
    block_reason: str = ""

class FeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    question: str
    response: str
    rating: str  # "positive" ou "negative"

# ---------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Suffelkopie Chatbot API is running"}

@app.get("/stats")
def stats():
    logs = load_logs()
    total = len(logs)
    cached = sum(1 for l in logs if l.get("cached"))
    blocked = sum(1 for l in logs if l.get("blocked"))
    positive = sum(1 for l in logs if l.get("rating") == "positive")
    negative = sum(1 for l in logs if l.get("rating") == "negative")
    return {
        "total_messages": total,
        "cached_responses": cached,
        "blocked_requests": blocked,
        "positive_ratings": positive,
        "negative_ratings": negative,
        "cache_stats": semantic_cache.stats(),
        "active_sessions": len(conversations)
    }

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    question = request.message.strip()
    session_id = request.session_id
    message_id = str(uuid.uuid4())

    if not question:
        return MessageResponse(
            response="Veuillez entrer un message.",
            message_id=message_id,
            blocked=True
        )

    # 🛡️ INPUT GUARDRAIL
    input_check = check_input(question)
    if not input_check.allowed:
        save_log({
            "message_id": message_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": "BLOCKED",
            "blocked": True,
            "block_reason": input_check.reason,
            "cached": False,
            "rating": None
        })
        return MessageResponse(
            response="Je suis désolé, je ne peux pas répondre à cette question. Je suis ici pour vous aider concernant nos produits et services. 😊",
            message_id=message_id,
            blocked=True,
            block_reason=input_check.reason
        )

    # ⚡ CACHE
    cached_response, score = semantic_cache.get(question)
    if cached_response:
        save_log({
            "message_id": message_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": cached_response,
            "blocked": False,
            "cached": True,
            "cache_score": round(score, 3),
            "rating": None
        })
        return MessageResponse(
            response=cached_response,
            message_id=message_id,
            cached=True
        )

    # 🤖 AGENT
    if session_id not in conversations:
       conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": question})
    if len(conversations[session_id]) > 10:
       conversations[session_id] = conversations[session_id][-10:]

    try:
        response = agent.invoke({"messages": conversations[session_id]})
        raw_answer = response["messages"][-1].content
        # 🛡️ OUTPUT GUARDRAIL
        output_check = check_output(raw_answer)
        final_answer = output_check.final_response

        conversations[session_id].append({"role": "assistant", "content": final_answer})
        semantic_cache.set(question, final_answer)

        save_log({
            "message_id": message_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": final_answer,
            "blocked": False,
            "cached": False,
            "rating": None
        })

        return MessageResponse(
            response=final_answer,
            message_id=message_id,
            cached=False
        )

    except Exception as e:
        return MessageResponse(
            response="Une erreur est survenue. Veuillez réessayer.",
            message_id=message_id,
            blocked=True,
            block_reason=str(e)
        )

@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    """Enregistre le feedback 👍/👎 du client."""
    logs = load_logs()
    for log in logs:
        if log.get("message_id") == request.message_id:
            log["rating"] = request.rating
            break
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    return {"status": "Feedback enregistré"}

@app.get("/logs")
def get_logs():
    """Retourne tous les logs pour analytics."""
    return load_logs()

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id in conversations:
        del conversations[session_id]
    return {"status": "Session cleared"}