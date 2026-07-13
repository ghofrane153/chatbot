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

def extract_text(field):
    """Extrait le texte d'un champ qui peut être une string simple
    OU une liste multilingue [{'id': '1', 'value': '...'}, ...]"""
    if isinstance(field, list):
        return field[0].get("value", "") if field else ""
    elif isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""

def normalize_product(p):
    price_raw = p.get("price", "0")
    try:
        price_formatted = f"{float(price_raw):.2f}"
    except:
        price_formatted = price_raw
    return {
        "id": p.get("id"),
        "name": extract_text(p.get("name", "")),
        "reference": extract_text(p.get("reference", "")) or p.get("reference", ""),
        "price": price_formatted
    }

@tool
def search_products(query: str) -> str:
    """Cherche des produits par nom ou référence dans le catalogue."""
    data = call_api("products", {"display": "[id,name,price,reference]"})
    raw_products = data.get("products", [])
    products = [normalize_product(p) for p in raw_products]
    results = [
        p for p in products
        if query.lower() in p["name"].lower() or query.lower() in str(p["reference"]).lower()
    ]
    if not results:
        return "Aucun produit trouvé."
    return "\n".join([
        f"- {p['name']} | Réf: {p['reference']} | Prix: {p['price']} €"
        for p in results
    ])

@tool
def get_all_products(dummy: str = "") -> str:
    """Retourne la liste des produits du catalogue (max 20)."""
    data = call_api("products", {"display": "[id,name,price,reference]", "limit": "20"})
    products = data.get("products", [])
    if not products:
        return "Aucun produit disponible."
    # Normalise et limite
    normalized = [normalize_product(p) for p in products[:20]]
    return "\n".join([
        f"- {p['name']} | Réf: {p['reference']} | Prix: {p['price']} €"
        for p in normalized
    ])

@tool
def get_most_expensive_product(dummy: str = "") -> str:
    """Retourne le produit le plus cher du catalogue."""
    data = call_api("products", {"display": "[id,name,price,reference]"})
    raw_products = data.get("products", [])
    products = [normalize_product(p) for p in raw_products]
    if not products:
        return "Aucun produit disponible."
    product = max(products, key=lambda p: float(p["price"]))
    return f"{product['name']} | Réf: {product['reference']} | Prix: {product['price']} €"

@tool
def get_cheapest_product(dummy: str = "") -> str:
    """Retourne le produit le moins cher du catalogue."""
    data = call_api("products", {"display": "[id,name,price,reference]"})
    raw_products = data.get("products", [])
    products = [normalize_product(p) for p in raw_products]
    if not products:
        return "Aucun produit disponible."
    product = min(products, key=lambda p: float(p["price"]))
    return f"{product['name']} | Réf: {product['reference']} | Prix: {product['price']} €"

@tool
def get_products_by_price_range(price_range: str) -> str:
    """Retourne les produits dans une fourchette de prix. Format: 'min,max' ex: '10,50'"""
    try:
        min_price, max_price = map(float, price_range.split(","))
        data = call_api("products", {"display": "[id,name,price,reference]"})
        raw_products = data.get("products", [])
        products = [normalize_product(p) for p in raw_products]
        results = [
            p for p in products
            if min_price <= float(p["price"]) <= max_price
        ]
        if not results:
            return f"Aucun produit entre {min_price}€ et {max_price}€."
        return "\n".join([
            f"- {p['name']} | Réf: {p['reference']} | Prix: {p['price']} €"
            for p in results
        ])
    except Exception as e:
        return "Format invalide. Utilise 'min,max' ex: '10,50'"

@tool
def get_product_description(product_name: str) -> str:
    """Retourne la description complète d'un produit."""
    data = call_api("products", {"display": "[id,name,price,reference,description_short]"})
    raw_products = data.get("products", [])
    
    results = []
    for p in raw_products:
        name = extract_text(p.get("name", ""))
        if product_name.lower() in name.lower():
            results.append(p)
    
    if not results:
        return "Produit non trouvé."
    
    p = results[0]
    name = extract_text(p.get("name", ""))
    desc = extract_text(p.get("description_short", ""))
    import re
    desc = re.sub('<[^<]+?>', ' ', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    return f"{name} | Prix: {p['price']} € \nDescription: {desc if desc else 'Pas de description disponible.'}"