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

ORDER_STATES = {
    "1": "En attente de paiement",
    "2": "Paiement accepté",
    "3": "En cours de préparation",
    "4": "Expédié",
    "5": "Livré",
    "6": "Annulé",
    "7": "Remboursé"
}

@tool
def admin_get_all_orders(dummy: str = "") -> str:
    """Liste toutes les commandes avec leur statut."""
    response = call_api("orders", params={
        "display": "[id,reference,current_state,total_paid,date_add]",
        "limit": "20",
        "sort": "[date_add_DESC]"
    })
    orders = response.json().get("orders", [])
    if not orders:
        return "Aucune commande trouvée."
    result = []
    for o in orders:
        state = ORDER_STATES.get(str(o.get("current_state", "")), "Inconnu")
        result.append(
            f"🛍️ Commande #{o.get('reference', o['id'])} | "
            f"Statut: {state} | "
            f"Total: {o.get('total_paid', '0')}€ | "
            f"Date: {o.get('date_add', '')[:10]}"
        )
    return f"📋 {len(orders)} dernières commandes:\n" + "\n".join(result)

@tool
def admin_get_orders_by_status(status: str) -> str:
    """
    Liste les commandes par statut.
    Statuts: 1=En attente, 2=Payé, 3=Préparation, 4=Expédié, 5=Livré, 6=Annulé
    """
    response = call_api("orders", params={
        "display": "[id,reference,current_state,total_paid,date_add]",
        "filter[current_state]": status
    })
    orders = response.json().get("orders", [])
    state_name = ORDER_STATES.get(status, "Inconnu")
    if not orders:
        return f"Aucune commande avec le statut '{state_name}'."
    result = []
    for o in orders:
        result.append(
            f"🛍️ #{o.get('reference', o['id'])} | "
            f"Total: {o.get('total_paid', '0')}€ | "
            f"Date: {o.get('date_add', '')[:10]}"
        )
    return f"📋 Commandes '{state_name}' ({len(orders)}):\n" + "\n".join(result)

@tool
def admin_get_order_details(order_id: str) -> str:
    """Récupère les détails complets d'une commande par son ID."""
    response = call_api(f"orders/{order_id}", params={"display": "full"})
    if response.status_code != 200:
        return f"❌ Commande ID {order_id} non trouvée."
    o = response.json().get("order", {})
    state = ORDER_STATES.get(str(o.get("current_state", "")), "Inconnu")
    return (f"📋 Commande #{o.get('reference', order_id)}\n"
            f"  Statut: {state}\n"
            f"  Total: {o.get('total_paid', '0')}€\n"
            f"  Date: {o.get('date_add', '')[:10]}\n"
            f"  Client ID: {o.get('id_customer', 'N/A')}\n"
            f"  Livraison: {o.get('total_shipping', '0')}€")

@tool
def admin_update_order_status(order_info: str) -> str:
    """
    Met à jour le statut d'une commande.
    Format: 'order_id,nouveau_statut' ex: '5,4' (commande 5 → Expédié)
    Statuts: 1=En attente, 2=Payé, 3=Préparation, 4=Expédié, 5=Livré, 6=Annulé
    """
    try:
        parts = order_info.split(",")
        order_id = parts[0].strip()
        new_state = parts[1].strip()
        response = call_api(f"orders/{order_id}", params={"display": "full"})
        if response.status_code != 200:
            return f"❌ Commande ID {order_id} non trouvée."
        order_data = response.json()
        order_data["order"]["current_state"] = new_state
        update_resp = call_api(
            f"orders/{order_id}",
            method="PUT",
            data=order_data
        )
        if update_resp.status_code in [200, 201]:
            state_name = ORDER_STATES.get(new_state, "Inconnu")
            return (f"✅ Statut de la commande #{order_id} mis à jour:\n"
                    f"  Nouveau statut: {state_name}")
        else:
            return f"❌ Erreur: {update_resp.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

@tool
def admin_get_pending_orders(dummy: str = "") -> str:
    """Liste toutes les commandes en attente de traitement."""
    result = []
    for state_id, state_name in [("1", "En attente de paiement"), ("3", "En préparation")]:
        response = call_api("orders", params={
            "display": "[id,reference,total_paid,date_add]",
            "filter[current_state]": state_id
        })
        orders = response.json().get("orders", [])
        for o in orders:
            result.append(
                f"⏳ [{state_name}] #{o.get('reference', o['id'])} | "
                f"Total: {o.get('total_paid', '0')}€"
            )
    if not result:
        return "✅ Aucune commande en attente !"
    return f"⏳ Commandes en attente ({len(result)}):\n" + "\n".join(result)