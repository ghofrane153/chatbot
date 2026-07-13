import re

# ---------------------------------------------------------
# Règles de vérification sur la RÉPONSE du bot
# ---------------------------------------------------------

PROMPT_LEAK_PATTERNS = [
    "system prompt", "you are a professional and friendly",
    "language rule", "your capabilities", "shop info:",
]

def check_prompt_leak(response: str) -> bool:
    """Détecte si la réponse fuite des morceaux du prompt système."""
    response_lower = response.lower()
    return any(pattern.lower() in response_lower for pattern in PROMPT_LEAK_PATTERNS)


def sanitize_response(response: str) -> str:
    """Nettoie la réponse de tout artefact technique qui ne devrait pas apparaître."""
    # Retire d'éventuelles balises ou JSON résiduels
    cleaned = re.sub(r'<function=.*?>', '', response)
    cleaned = re.sub(r'</function>', '', cleaned)
    return cleaned.strip()


class OutputGuardrailResult:
    def __init__(self, allowed: bool, final_response: str, reason: str = ""):
        self.allowed = allowed
        self.final_response = final_response
        self.reason = reason


def check_output(response: str) -> OutputGuardrailResult:
    """
    Vérifie et nettoie la réponse générée par l'agent avant envoi au client.
    """
    cleaned = sanitize_response(response)

    if check_prompt_leak(cleaned):
        return OutputGuardrailResult(
            allowed=False,
            final_response="Je suis désolé, je ne peux pas répondre à cette demande. Comment puis-je vous aider autrement ?",
            reason="Prompt leak detected"
        )

    if not cleaned or len(cleaned) < 2:
        return OutputGuardrailResult(
            allowed=False,
            final_response="Désolé, je n'ai pas pu générer de réponse. Pouvez-vous reformuler votre question ?",
            reason="Empty response"
        )

    return OutputGuardrailResult(allowed=True, final_response=cleaned)