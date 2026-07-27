import requests
import os
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PRESTASHOP_URL")
WS_KEY = os.getenv("PRESTASHOP_WS_KEY")

def call_api(endpoint, method="GET", params={}, data=None):
    base_params = {"ws_key": WS_KEY, "output_format": "JSON"}
    url = f"{BASE_URL}/api/{endpoint}"
    if method == "GET":
        response = requests.get(url, params={**base_params, **params})
    elif method == "PUT":
        response = requests.put(url, params=base_params, json=data)
    return response

def extract_text(field):
    if isinstance(field, list):
        return field[0].get("value", "") if field else ""
    elif isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""

@tool
def admin_check_stock(product_name: str) -> str:
    """Vérifie le stock d'un produit par son nom."""
    products_resp = call_api("products", params={"display": "[id,name,reference]"})
    products = products_resp.json().get("products", [])
    matched = None
    for p in products:
        name = extract_text(p.get("name", ""))
        if product_name.lower() in name.lower():
            matched = p
            break
    if not matched:
        return f"❌ Produit '{product_name}' non trouvé."
    product_id = matched["id"]
    name = extract_text(matched.get("name", ""))
    stock_resp = call_api("stock_availables", params={
        "display": "[id,id_product,quantity]",
        "filter[id_product]": product_id
    })
    stocks = stock_resp.json().get("stock_availables", [])
    if not stocks:
        return f"❌ Stock introuvable pour {name}."
    quantity = int(stocks[0]["quantity"])
    stock_id = stocks[0]["id"]
    status = "✅ En stock" if quantity > 0 else "❌ Rupture de stock"
    return (f"📦 Stock de '{name}':\n"
            f"  Quantité: {quantity} unité(s)\n"
            f"  Statut: {status}\n"
            f"  Stock ID: {stock_id}")

@tool
def admin_get_all_stocks(dummy: str = "") -> str:
    """Liste le stock de tous les produits."""
    products_resp = call_api("products", params={"display": "[id,name,reference]"})
    products = products_resp.json().get("products", [])
    stock_resp = call_api("stock_availables", params={"display": "[id_product,quantity]"})
    stocks = stock_resp.json().get("stock_availables", [])
    stock_dict = {str(s["id_product"]): int(s["quantity"]) for s in stocks}
    result = []
    for p in products:
        name = extract_text(p.get("name", ""))
        qty = stock_dict.get(str(p["id"]), 0)
        status = "✅" if qty > 0 else "❌"
        result.append(f"{status} {name} | Stock: {qty}")
    in_stock = sum(1 for s in stock_dict.values() if s > 0)
    out_of_stock = len(products) - in_stock
    return (f"📊 Rapport stock ({len(products)} produits):\n"
            f"✅ En stock: {in_stock} | ❌ Rupture: {out_of_stock}\n\n"
            + "\n".join(result))

@tool
def admin_update_stock(stock_info: str) -> str:
    """
    Met à jour le stock d'un produit.
    Format: 'product_id,nouvelle_quantite' ex: '5,100'
    """
    try:
        parts = stock_info.split(",")
        product_id = parts[0].strip()
        new_quantity = int(parts[1].strip())
        stock_resp = call_api("stock_availables", params={
            "display": "[id,id_product,quantity]",
            "filter[id_product]": product_id
        })
        stocks = stock_resp.json().get("stock_availables", [])
        if not stocks:
            return f"❌ Stock introuvable pour le produit ID {product_id}."
        stock_id = stocks[0]["id"]
        stock_data = {
            "stock_available": {
                "id": stock_id,
                "id_product": product_id,
                "id_product_attribute": "0",
                "quantity": str(new_quantity)
            }
        }
        update_resp = call_api(
            f"stock_availables/{stock_id}",
            method="PUT",
            data=stock_data
        )
        if update_resp.status_code in [200, 201]:
            return (f"✅ Stock mis à jour!\n"
                    f"  Produit ID: {product_id}\n"
                    f"  Nouvelle quantité: {new_quantity} unité(s)")
        else:
            return f"❌ Erreur lors de la mise à jour: {update_resp.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}\nFormat attendu: 'product_id,nouvelle_quantite'"

@tool
def admin_get_low_stock_products(threshold: str = "5") -> str:
    """
    Liste les produits avec un stock faible.
    Format: 'seuil' ex: '10' pour les produits avec moins de 10 unités
    """
    try:
        threshold_val = int(threshold)
        products_resp = call_api("products", params={"display": "[id,name,reference]"})
        products = products_resp.json().get("products", [])
        stock_resp = call_api("stock_availables", params={"display": "[id_product,quantity]"})
        stocks = stock_resp.json().get("stock_availables", [])
        stock_dict = {str(s["id_product"]): int(s["quantity"]) for s in stocks}
        low_stock = []
        for p in products:
            qty = stock_dict.get(str(p["id"]), 0)
            if qty <= threshold_val:
                name = extract_text(p.get("name", ""))
                status = "❌ Rupture" if qty == 0 else "⚠️ Faible"
                low_stock.append(f"{status} | {name} | Stock: {qty}")
        if not low_stock:
            return f"✅ Tous les produits ont un stock supérieur à {threshold_val}."
        return (f"⚠️ Produits avec stock ≤ {threshold_val} ({len(low_stock)} produits):\n"
                + "\n".join(low_stock))
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

@tool
def admin_add_stock(stock_info: str) -> str:
    """
    Ajoute des unités au stock existant d'un produit.
    Format: 'product_id,quantite_a_ajouter' ex: '5,20'
    """
    try:
        parts = stock_info.split(",")
        product_id = parts[0].strip()
        qty_to_add = int(parts[1].strip())
        stock_resp = call_api("stock_availables", params={
            "display": "[id,id_product,quantity]",
            "filter[id_product]": product_id
        })
        stocks = stock_resp.json().get("stock_availables", [])
        if not stocks:
            return f"❌ Stock introuvable pour le produit ID {product_id}."
        stock_id = stocks[0]["id"]
        current_qty = int(stocks[0]["quantity"])
        new_qty = current_qty + qty_to_add
        stock_data = {
            "stock_available": {
                "id": stock_id,
                "id_product": product_id,
                "id_product_attribute": "0",
                "quantity": str(new_qty)
            }
        }
        update_resp = call_api(
            f"stock_availables/{stock_id}",
            method="PUT",
            data=stock_data
        )
        if update_resp.status_code in [200, 201]:
            return (f"✅ Stock mis à jour!\n"
                    f"  Produit ID: {product_id}\n"
                    f"  Stock précédent: {current_qty}\n"
                    f"  Ajout: +{qty_to_add}\n"
                    f"  Nouveau stock: {new_qty}")
        else:
            return f"❌ Erreur: {update_resp.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"