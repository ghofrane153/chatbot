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
def check_product_stock(product_name: str) -> str:
    """Vérifie si un produit est disponible en stock."""
    # 1. Chercher le produit par nom
    data = call_api("products", {"display": "[id,name,reference]"})
    products = data.get("products", [])
    results = [
        p for p in products
        if product_name.lower() in p["name"].lower()
    ]
    if not results:
        return "Produit non trouvé."

    product = results[0]
    product_id = product["id"]

    # 2. Vérifier le stock
    stock_data = call_api("stock_availables", {
        "display": "[id,id_product,quantity]",
        "filter[id_product]": product_id
    })
    stocks = stock_data.get("stock_availables", [])

    if not stocks:
        return f"Impossible de vérifier le stock pour {product['name']}."

    quantity = int(stocks[0]["quantity"])

    if quantity > 0:
        return (f"✅ {product['name']} est disponible en stock. "
                f"Quantité: {quantity} unité(s).")
    else:
        return f"❌ {product['name']} est actuellement en rupture de stock."

@tool
def get_all_available_products(dummy: str = "") -> str:
    """Retourne tous les produits disponibles en stock."""
    # 1. Récupérer tous les produits
    products_data = call_api("products", {"display": "[id,name,price,reference]"})
    products = products_data.get("products", [])

    # 2. Récupérer tous les stocks
    stock_data = call_api("stock_availables", {
        "display": "[id_product,quantity]"
    })
    stocks = stock_data.get("stock_availables", [])

    # 3. Créer un dictionnaire stock par produit
    stock_dict = {s["id_product"]: int(s["quantity"]) for s in stocks}

    # 4. Filtrer les produits disponibles
    available = [
        p for p in products
        if stock_dict.get(str(p["id"]), 0) > 0
    ]

    if not available:
        return "Aucun produit disponible en stock actuellement."

    return "\n".join([
        f"- {p['name']} | Réf: {p['reference']} | Prix: {p['price']} € | Stock: {stock_dict.get(str(p['id']), 0)} unité(s)"
        for p in available
    ])

@tool
def get_out_of_stock_products(dummy: str = "") -> str:
    """Retourne tous les produits en rupture de stock."""
    products_data = call_api("products", {"display": "[id,name,price,reference]"})
    products = products_data.get("products", [])

    stock_data = call_api("stock_availables", {"display": "[id_product,quantity]"})
    stocks = stock_data.get("stock_availables", [])

    stock_dict = {s["id_product"]: int(s["quantity"]) for s in stocks}

    out_of_stock = [
        p for p in products
        if stock_dict.get(str(p["id"]), 0) <= 0
    ]

    if not out_of_stock:
        return "Tous les produits sont disponibles en stock !"

    return "\n".join([
        f"- {p['name']} | Réf: {p['reference']} | ❌ Rupture de stock"
        for p in out_of_stock
    ])