import os
import sys
import json
import uuid
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from admin.agent.admin_agent import (
    create_admin_chatbot, WRITE_TOOL_NAMES, write_checkpointer
)
from admin.tools.admin_report_tools import (
    admin_global_report, admin_revenue_report,
    admin_customer_report, admin_stock_report
)
from admin.tools.admin_stock_tools import admin_get_low_stock_products
from admin.tools.admin_product_tools import admin_get_all_products
from admin.tools.admin_order_tools import admin_get_pending_orders

load_dotenv()

app = FastAPI(title="Suffelkopie Admin Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_TOKEN = os.getenv("ADMIN_SECRET_TOKEN", "admin_suffelkopie_2024")
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="❌ Token invalide")
    return credentials.credentials

admin_bot = create_admin_chatbot()
ADMIN_LOG_FILE = "logs/admin_logs.json"
hitl_state = {}

# ---------------------------------------------------------
# COMMANDES DIRECTES (sans LLM — instantané)
# ---------------------------------------------------------
DIRECT_COMMANDS = {
    "rapport global": lambda: admin_global_report.invoke({"dummy": ""}),
    "rapport globale": lambda: admin_global_report.invoke({"dummy": ""}),
    "rapport global de": lambda: admin_global_report.invoke({"dummy": ""}),
    "génère un rapport global": lambda: admin_global_report.invoke({"dummy": ""}),
    "stock faible": lambda: admin_get_low_stock_products.invoke({"threshold": "5"}),
    "commandes en attente": lambda: admin_get_pending_orders.invoke({"dummy": ""}),
    "rapport chiffre": lambda: admin_revenue_report.invoke({"dummy": ""}),
    "chiffre d'affaires": lambda: admin_revenue_report.invoke({"dummy": ""}),
    "rapport client": lambda: admin_customer_report.invoke({"dummy": ""}),
    "rapport stock": lambda: admin_stock_report.invoke({"dummy": ""}),
    "liste tous les produits": lambda: admin_get_all_products.invoke({"dummy": ""}),
    "liste tous les clients": lambda: admin_customer_report.invoke({"dummy": ""}),
}

def check_direct_command(message: str):
    """Vérifie si le message correspond à une commande directe sans LLM."""
    msg_lower = message.lower().strip()
    for key, func in DIRECT_COMMANDS.items():
        if key in msg_lower:
            try:
                return func()
            except Exception as e:
                return f"❌ Erreur: {str(e)}"
    return None

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
def save_admin_log(entry: dict):
    logs = []
    if os.path.exists(ADMIN_LOG_FILE):
        with open(ADMIN_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(entry)
    with open(ADMIN_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# DÉTECTION INTENTION ÉCRITURE
# ---------------------------------------------------------
def detect_write_intent(message: str) -> bool:
    write_keywords = [
        "modifie", "modifier", "mets à jour", "mettre à jour", "update",
        "change", "changer", "ajoute", "ajouter", "augmente",
        "active", "activer", "désactive", "désactiver",
        "stock à", "prix à", "statut", "expédié", "annule la commande"
    ]
    return any(kw in message.lower() for kw in write_keywords)

def build_confirmation_message(tool_name: str, tool_args: dict) -> str:
    messages = {
        "admin_update_product_price":
            f"⚠️ **Modification de prix**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
        "admin_update_stock":
            f"⚠️ **Mise à jour du stock**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
        "admin_add_stock":
            f"⚠️ **Ajout de stock**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
        "admin_update_order_status":
            f"⚠️ **Modification statut commande**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
        "admin_activate_deactivate_product":
            f"⚠️ **Activation/Désactivation produit**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
        "admin_activate_deactivate_customer":
            f"⚠️ **Activation/Désactivation client**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler.",
    }
    return messages.get(
        tool_name,
        f"⚠️ Action: **{tool_name}**\nArguments: {tool_args}\n\nTapez **oui** pour confirmer ou **non** pour annuler."
    )

# ---------------------------------------------------------
# MODÈLES
# ---------------------------------------------------------
class AdminMessageRequest(BaseModel):
    message: str
    session_id: str = "admin_default"

class AdminMessageResponse(BaseModel):
    response: str
    message_id: str
    requires_confirmation: bool = False
    pending_tool: str = ""
    pending_args: dict = {}

# ---------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "Suffelkopie Admin Chatbot API running on port 8002"}

@app.post("/admin/chat", response_model=AdminMessageResponse)
async def admin_chat(
    request: AdminMessageRequest,
    token: str = Depends(verify_token)
):
    question = request.message.strip()
    session_id = request.session_id
    message_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    try:
        # ---- CAS 1 : Action en attente de confirmation HITL ----
        if hitl_state.get(session_id, {}).get("pending"):
            answer_lower = question.lower().strip()

            if any(w in answer_lower for w in ["oui", "yes", "confirme", "ok", "valide"]):
                result = admin_bot.invoke_write_resume(config=config)
                answer = next(
                    (m.content for m in reversed(result["messages"])
                     if hasattr(m, "content") and m.content
                     and not hasattr(m, "tool_calls")),
                    "✅ Action exécutée avec succès."
                )
                tool_name = hitl_state[session_id].get("tool_name", "")
                hitl_state[session_id] = {"pending": False}
                save_admin_log({
                    "message_id": message_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "action": "CONFIRMED",
                    "tool": tool_name,
                    "response": answer
                })
                return AdminMessageResponse(
                    response=f"✅ Action confirmée !\n\n{answer}",
                    message_id=message_id
                )

            elif any(w in answer_lower for w in ["non", "no", "annule", "cancel", "stop"]):
                tool_name = hitl_state[session_id].get("tool_name", "")
                hitl_state[session_id] = {"pending": False}
                save_admin_log({
                    "message_id": message_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "action": "CANCELLED",
                    "tool": tool_name
                })
                return AdminMessageResponse(
                    response="❌ Action annulée. Comment puis-je vous aider autrement ?",
                    message_id=message_id
                )

        # ---- CAS 0 : Commande directe (sans LLM — instantané) ----
        direct_result = check_direct_command(question)
        if direct_result:
            save_admin_log({
                "message_id": message_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "response": direct_result,
                "action": "DIRECT"
            })
            return AdminMessageResponse(
                response=direct_result,
                message_id=message_id
            )

        # ---- CAS 2 : Intention d'écriture → Agent WRITE avec HITL ----
        if detect_write_intent(question):
            result = admin_bot.invoke_write(
                [{"role": "user", "content": question}],
                config=config
            )
            last_message = result["messages"][-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                tool_call = last_message.tool_calls[0]
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})

                hitl_state[session_id] = {
                    "pending": True,
                    "tool_name": tool_name,
                    "tool_args": tool_args
                }

                save_admin_log({
                    "message_id": message_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "action": "HITL_PAUSE",
                    "question": question,
                    "tool": tool_name,
                    "args": tool_args
                })

                return AdminMessageResponse(
                    response=build_confirmation_message(tool_name, tool_args),
                    message_id=message_id,
                    requires_confirmation=True,
                    pending_tool=tool_name,
                    pending_args=tool_args
                )

        # ---- CAS 3 : Lecture via LLM avec fallback ----
        answer = admin_bot.invoke_read(
            [{"role": "user", "content": question}]
        )

        save_admin_log({
            "message_id": message_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": answer,
            "action": "READ"
        })

        return AdminMessageResponse(response=answer, message_id=message_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/logs")
async def get_admin_logs(token: str = Depends(verify_token)):
    if os.path.exists(ADMIN_LOG_FILE):
        with open(ADMIN_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/admin/hitl-state/{session_id}")
async def get_hitl_state(session_id: str, token: str = Depends(verify_token)):
    return hitl_state.get(session_id, {"pending": False})

@app.delete("/admin/session/{session_id}")
async def clear_admin_session(session_id: str, token: str = Depends(verify_token)):
    if session_id in hitl_state:
        del hitl_state[session_id]
    return {"status": "Session supprimée"}