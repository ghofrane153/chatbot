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
    elif method == "POST":
        response = requests.post(url, params=base_params, json=data)
    elif method == "PUT":
        response = requests.put(url, params=base_params, json=data)
    elif method == "DELETE":
        response = requests.delete(url, params=base_params)
    return response

def extract_text(field):
    if isinstance(field, list):
        return field[0].get("value", "") if field else ""
    elif isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""

@tool
def admin_get_all_products(dummy: str = "") -> str:
    """Liste les 20 premiers produits avec prix, référence et stock."""
    response = call_api("products", params={
        "display": "[id,name,price,reference]",
        "limit": "20"  # ← ajoute cette limite
    })
    products = response.json().get("products", [])
    if not products:
        return "Aucun produit trouvé."
    result = []
    for p in products:
        name = extract_text(p.get("name", ""))
        price = f"{float(p.get('price', 0)):.2f}"
        ref = p.get("reference", "")
        result.append(f"ID:{p['id']} | {name} | Réf:{ref} | Prix:{price}€")
    return f"📦 {len(products)} produits (sur {len(products)}):\n" + "\n".join(result)

@tool
def admin_get_product_by_id(product_id: str) -> str:
    """Récupère les détails complets d'un produit par son ID."""
    response = call_api(f"products/{product_id}", params={"display": "full"})
    if response.status_code != 200:
        return f"❌ Produit ID {product_id} non trouvé."
    p = response.json().get("product", {})
    name = extract_text(p.get("name", ""))
    price = f"{float(p.get('price', 0)):.2f}"
    ref = p.get("reference", "")
    return (f"✅ Produit trouvé:\n"
            f"  ID: {product_id}\n"
            f"  Nom: {name}\n"
            f"  Référence: {ref}\n"
            f"  Prix: {price}€\n"
            f"  Actif: {p.get('active', '1')}")

@tool
def admin_search_product(query: str) -> str:
    """Recherche un produit par nom ou référence."""
    response = call_api("products", params={"display": "[id,name,price,reference]"})
    products = response.json().get("products", [])
    results = []
    for p in products:
        name = extract_text(p.get("name", ""))
        ref = str(p.get("reference", ""))
        if query.lower() in name.lower() or query.lower() in ref.lower():
            price = f"{float(p.get('price', 0)):.2f}"
            results.append(f"ID:{p['id']} | {name} | Réf:{ref} | Prix:{price}€")
    if not results:
        return f"❌ Aucun produit trouvé pour '{query}'."
    return f"🔍 Résultats pour '{query}':\n" + "\n".join(results)

@tool
def admin_update_product_price(product_info: str) -> str:
    """
    Met à jour le prix d'un produit.
    Format: 'product_id,nouveau_prix' ex: '5,19.99'
    """
    try:
        parts = product_info.split(",")
        product_id = parts[0].strip()
        new_price = float(parts[1].strip())

        # Récupérer le produit existant
        response = call_api(f"products/{product_id}", params={"display": "full"})
        if response.status_code != 200:
            return f"❌ Produit ID {product_id} non trouvé."

        product_data = response.json()
        product_data["product"]["price"] = str(new_price)

        # Mettre à jour
        update_response = call_api(
            f"products/{product_id}",
            method="PUT",
            data=product_data
        )
        if update_response.status_code in [200, 201]:
            return f"✅ Prix du produit ID {product_id} mis à jour : {new_price}€"
        else:
            return f"❌ Erreur lors de la mise à jour: {update_response.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}\nFormat attendu: 'product_id,nouveau_prix'"

@tool
def admin_activate_deactivate_product(product_info: str) -> str:
    """
    Active ou désactive un produit.
    Format: 'product_id,1' pour activer ou 'product_id,0' pour désactiver
    """
    try:
        parts = product_info.split(",")
        product_id = parts[0].strip()
        active = parts[1].strip()

        response = call_api(f"products/{product_id}", params={"display": "full"})
        if response.status_code != 200:
            return f"❌ Produit ID {product_id} non trouvé."

        product_data = response.json()
        product_data["product"]["active"] = active

        update_response = call_api(
            f"products/{product_id}",
            method="PUT",
            data=product_data
        )
        if update_response.status_code in [200, 201]:
            status = "activé ✅" if active == "1" else "désactivé ❌"
            return f"Produit ID {product_id} {status}"
        else:
            return f"❌ Erreur: {update_response.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"