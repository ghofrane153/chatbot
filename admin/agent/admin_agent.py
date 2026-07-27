import os
import time
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from admin.tools.admin_product_tools import (
    admin_get_all_products, admin_get_product_by_id,
    admin_search_product, admin_update_product_price,
    admin_activate_deactivate_product
)
from admin.tools.admin_stock_tools import (
    admin_check_stock, admin_get_all_stocks,
    admin_update_stock, admin_get_low_stock_products,
    admin_add_stock
)
from admin.tools.admin_order_tools import (
    admin_get_all_orders, admin_get_orders_by_status,
    admin_get_order_details, admin_update_order_status,
    admin_get_pending_orders
)
from admin.tools.admin_report_tools import (
    admin_global_report, admin_revenue_report,
    admin_customer_report, admin_stock_report
)
from admin.tools.admin_customer_tools import (
    admin_get_all_customers, admin_get_customer_by_id,
    admin_search_customer, admin_get_customer_orders_count,
    admin_activate_deactivate_customer
)

ADMIN_SYSTEM_PROMPT = """Tu es un assistant administrateur professionnel pour la boutique Suffelkopie.
Tu aides les gestionnaires à gérer les produits, stocks, commandes et à générer des rapports.

TES CAPACITÉS:
1. PRODUITS: lister, rechercher, modifier le prix, activer/désactiver
2. STOCK: vérifier, mettre à jour, ajouter des unités, identifier les ruptures
3. COMMANDES: lister, filtrer par statut, voir les détails, mettre à jour le statut
4. CLIENTS: lister, rechercher, voir détails, historique des commandes, activer/désactiver
5. RAPPORTS: rapport global, chiffre d'affaires, clients, stocks

RÈGLES:
- Uniquement en français
- Données réelles uniquement via les outils
- Ne jamais inventer des données

FORMATS D'OUTILS:
- Modifier prix: 'product_id,nouveau_prix' ex: '5,19.99'
- Modifier stock: 'product_id,nouvelle_quantite' ex: '5,100'
- Ajouter stock: 'product_id,quantite_a_ajouter' ex: '5,20'
- Changer statut commande: 'order_id,nouveau_statut' ex: '5,4'
- Activer/désactiver produit: 'product_id,1' ou 'product_id,0'
- Activer/désactiver client: 'customer_id,1' ou 'customer_id,0'

STATUTS COMMANDES: 1=En attente, 2=Payé, 3=Préparation, 4=Expédié, 5=Livré, 6=Annulé
"""

# ---- Outils READ ONLY ----
READ_ONLY_TOOLS = [
    admin_get_all_products, admin_get_product_by_id,
    admin_search_product, admin_check_stock,
    admin_get_all_stocks, admin_get_low_stock_products,
    admin_get_all_orders, admin_get_orders_by_status,
    admin_get_order_details, admin_get_pending_orders,
    admin_get_all_customers, admin_get_customer_by_id,
    admin_search_customer, admin_get_customer_orders_count,
    admin_global_report, admin_revenue_report,
    admin_customer_report, admin_stock_report
]

# ---- Outils ÉCRITURE ----
WRITE_TOOLS = [
    admin_update_product_price,
    admin_activate_deactivate_product,
    admin_update_stock,
    admin_add_stock,
    admin_update_order_status,
    admin_activate_deactivate_customer
]

ALL_ADMIN_TOOLS = READ_ONLY_TOOLS + WRITE_TOOLS
WRITE_TOOL_NAMES = {tool.name for tool in WRITE_TOOLS}
write_checkpointer = MemorySaver()

def get_admin_providers():
    providers = []
    if os.getenv("GROQ_API_KEY"):
        providers.append(("Groq", ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
            max_tokens=1000
        )))
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("Gemini", ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0,
            max_output_tokens=1000
        )))
    if os.getenv("OPENROUTER_API_KEY"):
        providers.append(("OpenRouter", ChatOpenAI(
            model="mistralai/mistral-7b-instruct",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_tokens=1000
        )))
    if os.getenv("MISTRAL_API_KEY"):
        providers.append(("Mistral", ChatMistralAI(
            model="mistral-small-latest",
            api_key=os.getenv("MISTRAL_API_KEY"),
            temperature=0,
            max_tokens=1000
        )))
    if not providers:
        raise ValueError("❌ Aucun provider LLM configuré!")
    return providers

def create_admin_chatbot():
    providers = get_admin_providers()

    class AdminAgent:
        def __init__(self):
            self.providers = providers

        def _is_rate_limit(self, error_str: str) -> bool:
            return any(code in error_str for code in [
                "429", "413", "rate_limit", "quota",
                "resource_exhausted", "too many requests"
            ])

        def invoke_read(self, messages: list) -> str:
            """Lecture avec fallback automatique."""
            last_error = None
            for name, llm in self.providers:
                try:
                    print(f"🔄 Admin READ - Essai: {name}")
                    agent = create_react_agent(
                        model=llm,
                        tools=READ_ONLY_TOOLS,
                        prompt=ADMIN_SYSTEM_PROMPT
                    )
                    result = agent.invoke(
                        {"messages": messages},
                        config={"recursion_limit": 5}
                    )
                    print(f"✅ Admin READ - Succès: {name}")
                    for msg in reversed(result["messages"]):
                        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                            return msg.content
                    return result["messages"][-1].content
                except Exception as e:
                    last_error = e
                    if self._is_rate_limit(str(e).lower()):
                        print(f"⚠️ {name} rate limit → essai suivant dans 3s...")
                        time.sleep(3)
                    else:
                        print(f"❌ {name} erreur: {str(e)[:100]}")
                        time.sleep(1)
            raise Exception(f"Tous les providers ont échoué. Dernière erreur: {last_error}")

        def invoke_write(self, messages: list, config: dict):
            """Écriture avec HITL et fallback automatique."""
            last_error = None
            for name, llm in self.providers:
                try:
                    print(f"🔄 Admin WRITE - Essai: {name}")
                    agent = create_react_agent(
                        model=llm,
                        tools=WRITE_TOOLS,
                        prompt=ADMIN_SYSTEM_PROMPT,
                        checkpointer=write_checkpointer,
                        interrupt_before=["tools"]
                    )
                    result = agent.invoke(
                        {"messages": messages},
                        config=config
                    )
                    print(f"✅ Admin WRITE - Succès: {name}")
                    return result
                except Exception as e:
                    last_error = e
                    if self._is_rate_limit(str(e).lower()):
                        print(f"⚠️ {name} rate limit → essai suivant dans 3s...")
                        time.sleep(3)
                    else:
                        print(f"❌ {name} erreur: {str(e)[:100]}")
                        time.sleep(1)
            raise Exception(f"Tous les providers ont échoué. Dernière erreur: {last_error}")

        def invoke_write_resume(self, config: dict):
            """Reprend l'exécution après confirmation HITL."""
            last_error = None
            for name, llm in self.providers:
                try:
                    print(f"🔄 Admin WRITE RESUME - Essai: {name}")
                    agent = create_react_agent(
                        model=llm,
                        tools=WRITE_TOOLS,
                        prompt=ADMIN_SYSTEM_PROMPT,
                        checkpointer=write_checkpointer,
                        interrupt_before=["tools"]
                    )
                    result = agent.invoke(None, config=config)
                    print(f"✅ Admin WRITE RESUME - Succès: {name}")
                    return result
                except Exception as e:
                    last_error = e
                    if self._is_rate_limit(str(e).lower()):
                        print(f"⚠️ {name} rate limit → essai suivant dans 3s...")
                        time.sleep(3)
                    else:
                        print(f"❌ {name} erreur: {str(e)[:100]}")
                        time.sleep(1)
            raise Exception(f"Tous les providers ont échoué. Dernière erreur: {last_error}")

    return AdminAgent()