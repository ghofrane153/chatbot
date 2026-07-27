import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_URL = "http://localhost:8002";
const ADMIN_TOKEN = "admin_suffelkopie_2024";
const SESSION_ID = "admin_session_" + Math.random().toString(36).substr(2, 9);

const axiosAdmin = axios.create({
  baseURL: API_URL,
  headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
});

export default function AdminChat() {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "👋 Bonjour ! Je suis l'assistant administrateur Suffelkopie. Comment puis-je vous aider ?",
      requires_confirmation: false,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (messageText = null) => {
    const question = messageText || input.trim();
    if (!question || loading) return;
    setInput("");

    const userMsg = {
      id: "user_" + Date.now(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const tempId = "temp_" + Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "assistant",
        content: "...",
        typing: true,
      },
    ]);

    try {
      const res = await axiosAdmin.post("/admin/chat", {
        message: question,
        session_id: SESSION_ID,
      });

      const botMsg = {
        id: res.data.message_id,
        role: "assistant",
        content: res.data.response,
        requires_confirmation: res.data.requires_confirmation,
        pending_tool: res.data.pending_tool,
        pending_args: res.data.pending_args,
      };

      setMessages((prev) => prev.map((m) => (m.id === tempId ? botMsg : m)));

      if (res.data.requires_confirmation) {
        setPendingAction({
          tool: res.data.pending_tool,
          args: res.data.pending_args,
        });
      } else {
        setPendingAction(null);
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? {
                id: tempId,
                role: "assistant",
                content:
                  "❌ Une erreur est survenue. Vérifiez votre connexion.",
              }
            : m,
        ),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleConfirm = () => {
    setPendingAction(null);
    sendMessage("oui");
  };

  const handleCancel = () => {
    setPendingAction(null);
    sendMessage("non");
  };

  const quickActions = [
    "Rapport global",
    "Stock faible",
    "Commandes en attente",
    "Liste tous les produits",
    "Rapport chiffre d'affaires",
    "Liste tous les clients",
  ];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#f1f5f9",
        fontFamily: "'Segoe UI', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #1e3a5f, #2563eb)",
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
        }}
      >
        <div
          style={{
            width: "42px",
            height: "42px",
            background: "rgba(255,255,255,0.15)",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "20px",
          }}
        >
          ⚙️
        </div>
        <div>
          <div style={{ color: "#fff", fontWeight: "700", fontSize: "18px" }}>
            Suffelkopie — Admin Panel
          </div>
          <div style={{ color: "rgba(255,255,255,0.7)", fontSize: "13px" }}>
            Assistant administrateur intelligent
          </div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <span
            style={{
              background: "#22c55e",
              color: "#fff",
              padding: "4px 10px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: "600",
            }}
          >
            ● EN LIGNE
          </span>
        </div>
      </div>

      {/* Quick Actions */}
      <div
        style={{
          padding: "12px 16px",
          background: "#fff",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        {quickActions.map((action, i) => (
          <button
            key={i}
            onClick={() => sendMessage(action)}
            disabled={loading}
            style={{
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "20px",
              padding: "6px 14px",
              fontSize: "13px",
              cursor: loading ? "not-allowed" : "pointer",
              color: "#475569",
              transition: "all 0.2s",
              fontFamily: "inherit",
            }}
          >
            {action}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.map((msg) => (
          <div key={msg.id}>
            <div
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                alignItems: "flex-start",
                gap: "10px",
              }}
            >
              {/* Avatar assistant */}
              {msg.role === "assistant" && (
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    background: "linear-gradient(135deg, #1e3a5f, #2563eb)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "14px",
                    flexShrink: 0,
                  }}
                >
                  ⚙️
                </div>
              )}

              <div
                style={{
                  maxWidth: "70%",
                  padding: "12px 16px",
                  borderRadius:
                    msg.role === "user"
                      ? "16px 16px 4px 16px"
                      : "16px 16px 16px 4px",
                  background:
                    msg.role === "user"
                      ? "linear-gradient(135deg, #2563eb, #1d4ed8)"
                      : msg.requires_confirmation
                        ? "#fef3c7"
                        : "#fff",
                  color: msg.role === "user" ? "#fff" : "#1e293b",
                  fontSize: "14px",
                  lineHeight: "1.6",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                  border:
                    msg.role === "assistant"
                      ? msg.requires_confirmation
                        ? "1px solid #f59e0b"
                        : "1px solid #e2e8f0"
                      : "none",
                  whiteSpace: "pre-wrap",
                }}
              >
                {msg.typing ? (
                  <div
                    style={{
                      display: "flex",
                      gap: "4px",
                      alignItems: "center",
                    }}
                  >
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        style={{
                          width: "8px",
                          height: "8px",
                          background: "#94a3b8",
                          borderRadius: "50%",
                          animation: `bounce 1.2s ${i * 0.2}s infinite`,
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  msg.content
                )}
              </div>

              {/* Avatar user */}
              {msg.role === "user" && (
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    background: "#e2e8f0",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "14px",
                    flexShrink: 0,
                  }}
                >
                  👤
                </div>
              )}
            </div>

            {/* Boutons confirmation HITL */}
            {msg.requires_confirmation && (
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  marginTop: "10px",
                  marginLeft: "42px",
                }}
              >
                <button
                  onClick={handleConfirm}
                  disabled={loading}
                  style={{
                    background: "#22c55e",
                    color: "#fff",
                    border: "none",
                    borderRadius: "10px",
                    padding: "10px 24px",
                    cursor: loading ? "not-allowed" : "pointer",
                    fontWeight: "600",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    boxShadow: "0 2px 8px rgba(34,197,94,0.3)",
                    transition: "all 0.2s",
                  }}
                >
                  ✅ Confirmer
                </button>
                <button
                  onClick={handleCancel}
                  disabled={loading}
                  style={{
                    background: "#ef4444",
                    color: "#fff",
                    border: "none",
                    borderRadius: "10px",
                    padding: "10px 24px",
                    cursor: loading ? "not-allowed" : "pointer",
                    fontWeight: "600",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    boxShadow: "0 2px 8px rgba(239,68,68,0.3)",
                    transition: "all 0.2s",
                  }}
                >
                  ❌ Annuler
                </button>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "16px",
          background: "#fff",
          borderTop: "1px solid #e2e8f0",
          display: "flex",
          gap: "10px",
          alignItems: "flex-end",
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ex: Génère un rapport global, Mets à jour le stock du produit 5 à 100 unités..."
          rows={1}
          disabled={loading}
          style={{
            flex: 1,
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            padding: "12px 16px",
            fontSize: "14px",
            resize: "none",
            outline: "none",
            fontFamily: "inherit",
            lineHeight: "1.5",
            maxHeight: "120px",
            overflowY: "auto",
            background: loading ? "#f8fafc" : "#fff",
          }}
        />
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          style={{
            background:
              loading || !input.trim()
                ? "#94a3b8"
                : "linear-gradient(135deg, #2563eb, #1d4ed8)",
            border: "none",
            borderRadius: "12px",
            padding: "12px 20px",
            color: "#fff",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            fontSize: "18px",
            boxShadow:
              loading || !input.trim()
                ? "none"
                : "0 4px 12px rgba(37,99,235,0.4)",
            transition: "all 0.2s",
          }}
        >
          ➤
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}
