import { useState, useEffect, useRef } from "react";
import axios from "axios";

const SESSION_ID = "session_" + Math.random().toString(36).substr(2, 9);
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "👋 Bonjour ! Je suis l'assistant Suffelkopie. Comment puis-je vous aider ?",
      cached: false,
      rating: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendFeedback = async (messageId, question, response, rating) => {
    try {
      await axios.post(`${API_URL}/feedback`, {
        message_id: messageId,
        session_id: SESSION_ID,
        question,
        response,
        rating,
      });
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, rating } : m)),
      );
    } catch (err) {
      console.error("Feedback error:", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");

    const userMsg = {
      id: "user_" + Date.now(),
      role: "user",
      content: userMessage,
      rating: null,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    // Ajoute un message "typing" temporaire
    const tempId = "temp_" + Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "assistant",
        content: "...",
        typing: true,
        rating: null,
      },
    ]);

    try {
      const res = await axios.post(`${API_URL}/chat`, {
        message: userMessage,
        session_id: SESSION_ID,
      });

      const botMsg = {
        id: res.data.message_id,
        role: "assistant",
        content: res.data.response,
        cached: res.data.cached,
        blocked: res.data.blocked,
        rating: null,
        question: userMessage,
      };

      // Remplace le message "typing" par la vraie réponse
      setMessages((prev) => prev.map((m) => (m.id === tempId ? botMsg : m)));
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? {
                id: tempId,
                role: "assistant",
                content: "❌ Une erreur est survenue. Veuillez réessayer.",
                rating: null,
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

  return (
    <>
      <div
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 1000,
        }}
      >
        {isOpen && (
          <div
            style={{
              width: "380px",
              height: "580px",
              background: "#fff",
              borderRadius: "16px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
              display: "flex",
              flexDirection: "column",
              marginBottom: "16px",
              overflow: "hidden",
              border: "1px solid #e5e7eb",
            }}
          >
            {/* Header */}
            <div
              style={{
                background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "10px" }}
              >
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    background: "rgba(255,255,255,0.2)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "18px",
                  }}
                >
                  🤖
                </div>
                <div>
                  <div
                    style={{
                      color: "#fff",
                      fontWeight: "600",
                      fontSize: "15px",
                    }}
                  >
                    Suffelkopie
                  </div>
                  <div
                    style={{ color: "rgba(255,255,255,0.8)", fontSize: "12px" }}
                  >
                    Assistant en ligne
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#fff",
                  fontSize: "20px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {/* Messages */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                background: "#f9fafb",
              }}
            >
              {messages.map((msg) => (
                <div key={msg.id}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent:
                        msg.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "80%",
                        padding: "10px 14px",
                        borderRadius:
                          msg.role === "user"
                            ? "16px 16px 4px 16px"
                            : "16px 16px 16px 4px",
                        background: msg.role === "user" ? "#2563eb" : "#fff",
                        color: msg.role === "user" ? "#fff" : "#111827",
                        fontSize: "14px",
                        lineHeight: "1.5",
                        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                        border:
                          msg.role === "assistant"
                            ? "1px solid #e5e7eb"
                            : "none",
                      }}
                    >
                      {/* Typing animation */}
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
                                background: "#9ca3af",
                                borderRadius: "50%",
                                animation: `bounce 1.2s ${i * 0.2}s infinite`,
                              }}
                            />
                          ))}
                        </div>
                      ) : (
                        msg.content
                      )}

                      {/* Cache badge */}
                      {msg.cached && !msg.typing && (
                        <div
                          style={{
                            fontSize: "10px",
                            color: "#9ca3af",
                            marginTop: "4px",
                          }}
                        >
                          ⚡ Réponse instantanée
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Boutons 👍/👎 pour les messages du bot */}
                  {msg.role === "assistant" &&
                    !msg.typing &&
                    msg.id !== "welcome" && (
                      <div
                        style={{
                          display: "flex",
                          gap: "6px",
                          marginTop: "4px",
                          justifyContent: "flex-start",
                          paddingLeft: "4px",
                        }}
                      >
                        <button
                          onClick={() =>
                            sendFeedback(
                              msg.id,
                              msg.question,
                              msg.content,
                              "positive",
                            )
                          }
                          style={{
                            background:
                              msg.rating === "positive" ? "#dcfce7" : "#f3f4f6",
                            border:
                              msg.rating === "positive"
                                ? "1px solid #86efac"
                                : "1px solid #e5e7eb",
                            borderRadius: "8px",
                            padding: "2px 8px",
                            cursor: "pointer",
                            fontSize: "14px",
                            transition: "all 0.2s",
                          }}
                          title="Bonne réponse"
                        >
                          👍
                        </button>
                        <button
                          onClick={() =>
                            sendFeedback(
                              msg.id,
                              msg.question,
                              msg.content,
                              "negative",
                            )
                          }
                          style={{
                            background:
                              msg.rating === "negative" ? "#fee2e2" : "#f3f4f6",
                            border:
                              msg.rating === "negative"
                                ? "1px solid #fca5a5"
                                : "1px solid #e5e7eb",
                            borderRadius: "8px",
                            padding: "2px 8px",
                            cursor: "pointer",
                            fontSize: "14px",
                            transition: "all 0.2s",
                          }}
                          title="Mauvaise réponse"
                        >
                          👎
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
                padding: "12px 16px",
                borderTop: "1px solid #e5e7eb",
                background: "#fff",
                display: "flex",
                gap: "8px",
                alignItems: "flex-end",
              }}
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Écrivez votre message..."
                rows={1}
                style={{
                  flex: 1,
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  padding: "10px 14px",
                  fontSize: "14px",
                  resize: "none",
                  outline: "none",
                  fontFamily: "inherit",
                  lineHeight: "1.5",
                  maxHeight: "100px",
                  overflowY: "auto",
                }}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                style={{
                  background: loading || !input.trim() ? "#9ca3af" : "#2563eb",
                  border: "none",
                  borderRadius: "12px",
                  padding: "10px 16px",
                  color: "#fff",
                  cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                  fontSize: "18px",
                  transition: "background 0.2s",
                }}
              >
                ➤
              </button>
            </div>
          </div>
        )}

        {/* Bouton flottant */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            width: "60px",
            height: "60px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
            border: "none",
            cursor: "pointer",
            boxShadow: "0 4px 16px rgba(37,99,235,0.4)",
            fontSize: "26px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "transform 0.2s",
            marginLeft: "auto",
          }}
        >
          {isOpen ? "✕" : "💬"}
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </>
  );
}
