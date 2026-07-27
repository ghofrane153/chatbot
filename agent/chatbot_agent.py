import os
import time
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools.product_tools import (
    search_products, get_all_products, get_most_expensive_product,
    get_cheapest_product, get_products_by_price_range, get_product_description
)
from tools.stock_tools import (
    check_product_stock, get_all_available_products, get_out_of_stock_products
)
from tools.category_tools import get_all_categories, get_products_by_category
from tools.info_tools import get_all_info_pages, get_info_page_content

SYSTEM_PROMPT = """You are a professional and friendly customer service assistant for Suffelkopie, an online shop.

LANGUAGE RULE — CRITICAL:
- Detect the language of the customer's message automatically
- Always respond in the SAME language as the customer
- If the customer writes in German → respond in German
- If the customer writes in French → respond in French  
- If the customer writes in English → respond in English

YOUR CAPABILITIES:

1. PRODUCT QUESTIONS:
- Search products by name or reference
- Show full product catalogue
- Find cheapest or most expensive products
- Filter products by price range
- Show product descriptions
- Check product stock availability
- Show available or out-of-stock products
- List all categories
- Show products by category

2. PRODUCT RECOMMENDATIONS — CRITICAL RULES:
- When a customer describes a need, ALWAYS call get_all_products FIRST to see 
  the complete catalogue, then suggest the most relevant products from the list
- NEVER say "we don't have this product" without first calling get_all_products
- After getting all products, analyze EACH product name and find the best matches
  for the customer's need, even if the words are different
- Search with multiple keywords in different languages:
  Example: "liquid storage" → try "thermo", "iso", "kanne", "flasche", "bottle", "becher"
  Example: "gift" → try "geschenk", "cadeau", "set", "box", "tasche"
  Example: "bag" → try "tasche", "beutel", "tüte", "sac"
- If search_products returns nothing → ALWAYS fallback to get_all_products 
  and manually pick the most relevant products from the full list
- Always suggest 2-4 products with a brief explanation of why they match
- If truly nothing matches → show the full catalogue so the customer can choose

3. GENERAL SHOP INFORMATION:
- Use get_all_info_pages to see what information pages exist
- Use get_info_page_content to answer questions about legal notice, privacy policy,
  terms and conditions, about us, secure payment methods
- Always use these tools instead of guessing shop policies

RULES:
- NEVER invent products, prices, references, or stock information
- NEVER say a product doesn't exist without checking get_all_products first
- Be polite, professional, and helpful at all times
- Always greet the customer on their first message
- Keep responses clear, concise, and well structured
- When recommending products, briefly explain WHY each one fits the customer's need
- NEVER invent or assume product descriptions
- If you don't have the description, just show name, reference and price
- Only describe a product if you got the description from get_product_description tool

SHOP INFO:
- Shop name: Suffelkopie
- Currency: Euro (€)
- Languages: German, French, English
"""

TOOLS = [
    search_products, get_all_products, get_most_expensive_product,
    get_cheapest_product, get_products_by_price_range, get_product_description,
    check_product_stock, get_all_available_products, get_out_of_stock_products,
    get_all_categories, get_products_by_category,
    get_all_info_pages, get_info_page_content
]

# ---------------------------------------------------------
# PROVIDERS — ordre de priorité
# ---------------------------------------------------------

def get_providers():
    providers = []

    if os.getenv("GROQ_API_KEY"):
        providers.append({
            "name": "Groq",
            "llm": ChatGroq(
                model="llama-3.1-8b-instant",
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=0
            )
        })

    if os.getenv("GEMINI_API_KEY"):
        providers.append({
            "name": "Gemini",
            "llm": ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0
            )
        })

    if os.getenv("OPENROUTER_API_KEY"):
        providers.append({
            "name": "OpenRouter",
            "llm": ChatOpenAI(
                model="mistralai/mistral-7b-instruct",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                temperature=0
            )
        })

    if os.getenv("MISTRAL_API_KEY"):
        providers.append({
            "name": "Mistral",
            "llm": ChatMistralAI(
                model="mistral-small-latest",
                api_key=os.getenv("MISTRAL_API_KEY"),
                temperature=0
            )
        })

    return providers

# ---------------------------------------------------------
# FALLBACK AGENT
# ---------------------------------------------------------

def invoke_with_fallback(messages: list) -> str:
    """
    Essaie chaque provider dans l'ordre.
    Si rate limit → attend 5s et essaie le suivant.
    Si erreur autre → essaie le suivant directement.
    """
    providers = get_providers()

    if not providers:
        raise ValueError("❌ Aucun provider LLM configuré dans .env !")

    last_error = None
    for provider in providers:
        try:
            print(f"🔄 Essai avec : {provider['name']}")
            agent = create_react_agent(
                model=provider["llm"],
                tools=TOOLS,
                prompt=SYSTEM_PROMPT
            )
            response = agent.invoke({"messages": messages})
            print(f"✅ Succès avec : {provider['name']}")
            return response["messages"][-1].content

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            if "rate_limit" in error_str or "429" in error_str or "413" in error_str:
                print(f"⚠️ {provider['name']} rate limit → essai suivant dans 3s...")
                time.sleep(3)
            else:
                print(f"❌ {provider['name']} erreur: {str(e)[:100]} → essai suivant...")

    raise Exception(f"Tous les providers ont échoué. Dernière erreur: {last_error}")

# ---------------------------------------------------------
# CREATE CHATBOT (compatibilité avec server.py)
# ---------------------------------------------------------

def create_chatbot():
    """Retourne un objet avec méthode invoke qui utilise le fallback."""
    class FallbackAgent:
        def invoke(self, inputs):
            messages = inputs.get("messages", [])
            answer = invoke_with_fallback(messages)
            return {"messages": [type('msg', (), {'content': answer})()]}
    return FallbackAgent()