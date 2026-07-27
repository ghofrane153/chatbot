import requests
import os
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PRESTASHOP_URL")
WS_KEY = os.getenv("PRESTASHOP_WS_KEY_SUFFELKOPIE")


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
def admin_get_all_customers(dummy: str = "") -> str:
    """Liste tous les clients avec nom, email et statut actif/inactif."""
    response = call_api(
        "customers",
        params={"display": "[id,firstname,lastname,email,active]"}
    )
    if response.status_code != 200:
        return f"❌ Erreur API: {response.status_code}"
    customers = response.json().get("customers", [])
    if not customers:
        return "Aucun client trouvé."
    result = []
    for c in customers:
        firstname = extract_text(c.get("firstname", ""))
        lastname = extract_text(c.get("lastname", ""))
        email = c.get("email", "")
        active = "✅" if str(c.get("active", "1")) == "1" else "❌"
        result.append(f"ID:{c['id']} | {firstname} {lastname} | {email} | Actif:{active}")
    return f"👤 {len(customers)} clients trouvés:\n" + "\n".join(result)


@tool
def admin_get_customer_by_id(customer_id: str) -> str:
    """Récupère les détails complets d'un client par son ID."""
    response = call_api(f"customers/{customer_id}", params={"display": "full"})
    if response.status_code != 200:
        return f"❌ Client ID {customer_id} non trouvé."
    c = response.json().get("customer", {})
    firstname = extract_text(c.get("firstname", ""))
    lastname = extract_text(c.get("lastname", ""))
    email = c.get("email", "")
    active = "Oui" if str(c.get("active", "1")) == "1" else "Non"
    date_add = c.get("date_add", "")
    company = extract_text(c.get("company", "")) or "N/A"
    return (
        f"✅ Client trouvé:\n"
        f"  ID: {customer_id}\n"
        f"  Nom: {firstname} {lastname}\n"
        f"  Email: {email}\n"
        f"  Société: {company}\n"
        f"  Actif: {active}\n"
        f"  Inscrit le: {date_add}"
    )


@tool
def admin_search_customer(query: str) -> str:
    """Recherche un client par nom, prénom ou email."""
    response = call_api(
        "customers",
        params={"display": "[id,firstname,lastname,email,active]"}
    )
    if response.status_code != 200:
        return f"❌ Erreur API: {response.status_code}"
    customers = response.json().get("customers", [])
    results = []
    for c in customers:
        firstname = extract_text(c.get("firstname", ""))
        lastname = extract_text(c.get("lastname", ""))
        email = str(c.get("email", ""))
        haystack = f"{firstname} {lastname} {email}".lower()
        if query.lower() in haystack:
            active = "✅" if str(c.get("active", "1")) == "1" else "❌"
            results.append(f"ID:{c['id']} | {firstname} {lastname} | {email} | Actif:{active}")
    if not results:
        return f"❌ Aucun client trouvé pour '{query}'."
    return f"🔍 Résultats pour '{query}':\n" + "\n".join(results)


@tool
def admin_get_customer_orders_count(customer_id: str) -> str:
    """Récupère le nombre de commandes d'un client via son ID."""
    response = call_api(
        "orders",
        params={"filter[id_customer]": f"[{customer_id}]", "display": "[id,total_paid,current_state]"}
    )
    if response.status_code != 200:
        return f"❌ Erreur API: {response.status_code}"
    orders = response.json().get("orders", [])
    if not orders:
        return f"Le client ID {customer_id} n'a passé aucune commande."
    total_spent = sum(float(o.get("total_paid", 0)) for o in orders)
    return (
        f"📦 Client ID {customer_id}: {len(orders)} commande(s)\n"
        f"💰 Total dépensé: {total_spent:.2f}€"
    )


@tool
def admin_activate_deactivate_customer(customer_info: str) -> str:
    """
    Active ou désactive un compte client.
    Format: 'customer_id,1' pour activer ou 'customer_id,0' pour désactiver
    """
    try:
        parts = customer_info.split(",")
        customer_id = parts[0].strip()
        active = parts[1].strip()

        response = call_api(f"customers/{customer_id}", params={"display": "full"})
        if response.status_code != 200:
            return f"❌ Client ID {customer_id} non trouvé."

        customer_data = response.json()
        customer_data["customer"]["active"] = active

        update_response = call_api(
            f"customers/{customer_id}",
            method="PUT",
            data=customer_data
        )
        if update_response.status_code in [200, 201]:
            status = "activé ✅" if active == "1" else "désactivé ❌"
            return f"Client ID {customer_id} {status}"
        else:
            return f"❌ Erreur: {update_response.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}\nFormat attendu: 'customer_id,1' ou 'customer_id,0'"