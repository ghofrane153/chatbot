import requests
import os
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PRESTASHOP_URL")
WS_KEY = os.getenv("PRESTASHOP_WS_KEY")

def call_api(endpoint, params={}):
    base_params = {
        "ws_key": WS_KEY,
        "output_format": "JSON"
    }
    response = requests.get(f"{BASE_URL}/api/{endpoint}", params={**base_params, **params})
    return response.json()

@tool
def get_all_categories(dummy: str = "") -> str:
    """Retourne toutes les catégories disponibles dans la boutique."""
    data = call_api("categories", {"display": "[id,name]"})
    categories = data.get("categories", [])
    if not categories:
        return "Aucune catégorie disponible."
    result = []
    for c in categories:
        name = c.get("name", {})
        if isinstance(name, dict):
            lang = name.get("language", [{}])
            name = lang[0].get("#text", "") if isinstance(lang, list) else ""
        result.append(f"- {name} (ID: {c['id']})")
    return "\n".join(result)

@tool
def get_products_by_category(category_name: str) -> str:
    """Retourne les produits d'une catégorie spécifique."""
    # 1. Trouver la catégorie
    data = call_api("categories", {"display": "[id,name]"})
    categories = data.get("categories", [])
    category_id = None
    for c in categories:
        name = c.get("name", {})
        if isinstance(name, dict):
            lang = name.get("language", [{}])
            name = lang[0].get("#text", "") if isinstance(lang, list) else ""
        if category_name.lower() in str(name).lower():
            category_id = c["id"]
            break
    if not category_id:
        return f"Catégorie '{category_name}' non trouvée."

    # 2. Récupérer les produits de cette catégorie
    products_data = call_api("products", {
        "display": "[id,name,price,reference]",
        "filter[id_category_default]": category_id
    })
    products = products_data.get("products", [])
    if not products:
        return f"Aucun produit trouvé dans la catégorie '{category_name}'."
    return "\n".join([
        f"- {p['name']} | Réf: {p['reference']} | Prix: {p['price']} €"
        for p in products
    ])