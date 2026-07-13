from dotenv import load_dotenv
from agent.chatbot_agent import create_chatbot
from guardrails.input_guardrails import check_input
from guardrails.output_guardrails import check_output
from cache.semantic_cache import semantic_cache

load_dotenv()

agent = create_chatbot()

print("=" * 50)
print("🤖 Suffelkopie Chatbot")
print("Languages: Deutsch | Français | English")
print("Type 'quit' to exit")
print(semantic_cache.stats())
print("=" * 50)

conversation_history = []

while True:
    question = input("\nYou: ").strip()

    if not question:
        continue

    if question.lower() == "quit":
        print("Goodbye! / Au revoir! / Auf Wiedersehen!")
        break

    # 🛡️ INPUT GUARDRAIL
    input_check = check_input(question)
    if not input_check.allowed:
        print(f"\nBot: Je suis désolé, je ne peux pas répondre à cette question. "
              f"Je suis ici pour vous aider concernant nos produits et services. 😊\n")
        continue

    # ⚡ VÉRIFICATION CACHE SÉMANTIQUE
    cached_response, score = semantic_cache.get(question)
    if cached_response:
        print(f"\n⚡ [Cache hit: {score:.2f}] Bot: {cached_response}\n")
        conversation_history.append({"role": "user", "content": question})
        conversation_history.append({"role": "assistant", "content": cached_response})
        continue

    # 🤖 APPEL AGENT (si pas en cache)
    conversation_history.append({"role": "user", "content": question})

    try:
        response = agent.invoke({"messages": conversation_history})
        raw_answer = response["messages"][-1].content

        # 🛡️ OUTPUT GUARDRAIL
        output_check = check_output(raw_answer)
        final_answer = output_check.final_response

        conversation_history.append({"role": "assistant", "content": final_answer})

        # 💾 MISE EN CACHE
        semantic_cache.set(question, final_answer)

        print(f"\nBot: {final_answer}\n")

    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}\n")