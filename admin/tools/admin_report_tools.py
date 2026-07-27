import requests
import os
from langchain_core.tools import tool
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

BASE_URL = os.getenv("PRESTASHOP_URL")
WS_KEY = os.getenv("PRESTASHOP_WS_KEY")

def call_api(endpoint, params={}):
    base_params = {"ws_key": WS_KEY, "output_format": "JSON"}
    response = requests.get(f"{BASE_URL}/api/{endpoint}", params={**base_params, **params})
    return response.json()

def extract_text(field):
    if isinstance(field, list):
        return field[0].get("value", "") if field else ""
    elif isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""

@tool
def admin_global_report(dummy: str = "") -> str:
    """Génère un rapport global de la boutique."""
    products_data = call_api("products", {"display": "[id,name,price]"})
    products = products_data.get("products", [])

    stock_data = call_api("stock_availables", {"display": "[id_product,quantity]"})
    stocks = stock_data.get("stock_availables", [])
    stock_dict = {str(s["id_product"]): int(s["quantity"]) for s in stocks}

    orders_data = call_api("orders", {"display": "[id,total_paid,current_state]"})
    orders = orders_data.get("orders", [])

    customers_data = call_api("customers", {"display": "[id]"})
    customers = customers_data.get("customers", [])

    total_products = len(products)
    in_stock = sum(1 for p in products if stock_dict.get(str(p["id"]), 0) > 0)
    out_of_stock = total_products - in_stock
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total_paid", 0)) for o in orders)
    completed_orders = sum(1 for o in orders if str(o.get("current_state")) == "5")
    total_customers = len(customers)
    prices = [float(p.get("price", 0)) for p in products]
    avg_price = sum(prices) / len(prices) if prices else 0

    return (f"📊 RAPPORT GLOBAL SUFFELKOPIE\n"
            f"{'='*40}\n"
            f"📦 PRODUITS:\n"
            f"  Total: {total_products}\n"
            f"  En stock: {in_stock} ✅\n"
            f"  Rupture: {out_of_stock} ❌\n"
            f"  Prix moyen: {avg_price:.2f}€\n\n"
            f"🛍️ COMMANDES:\n"
            f"  Total: {total_orders}\n"
            f"  Livrées: {completed_orders}\n"
            f"  Chiffre d'affaires: {total_revenue:.2f}€\n\n"
            f"👥 CLIENTS:\n"
            f"  Total: {total_customers}\n"
            f"{'='*40}")

@tool
def admin_revenue_report(dummy: str = "") -> str:
    """Calcule le chiffre d'affaires total et par statut de commande."""
    orders_data = call_api("orders", {
        "display": "[id,reference,total_paid,current_state,date_add]"
    })
    orders = orders_data.get("orders", [])
    if not orders:
        return "Aucune commande trouvée."

    ORDER_STATES = {
        "1": "En attente", "2": "Payé", "3": "Préparation",
        "4": "Expédié", "5": "Livré", "6": "Annulé", "7": "Remboursé"
    }

    total = sum(float(o.get("total_paid", 0)) for o in orders)
    by_state = {}
    for o in orders:
        state = ORDER_STATES.get(str(o.get("current_state", "")), "Inconnu")
        amount = float(o.get("total_paid", 0))
        by_state[state] = by_state.get(state, 0) + amount

    result = [f"💰 RAPPORT CHIFFRE D'AFFAIRES\n{'='*40}"]
    result.append(f"Total général: {total:.2f}€")
    result.append(f"\nDétail par statut:")
    for state, amount in sorted(by_state.items(), key=lambda x: x[1], reverse=True):
        result.append(f"  {state}: {amount:.2f}€")

    return "\n".join(result)

@tool
def admin_customer_report(dummy: str = "") -> str:
    """Génère un rapport sur les clients."""
    customers_data = call_api("customers", {
        "display": "[id,firstname,lastname,email,date_add,active]"
    })
    customers = customers_data.get("customers", [])
    if not customers:
        return "Aucun client trouvé."

    active = sum(1 for c in customers if str(c.get("active", "0")) == "1")
    inactive = len(customers) - active

    recent = sorted(customers, key=lambda x: x.get("date_add", ""), reverse=True)[:5]
    recent_list = []
    for c in recent:
        name = f"{c.get('firstname', '')} {c.get('lastname', '')}"
        date = c.get("date_add", "")[:10]
        recent_list.append(f"  👤 {name} | {c.get('email', '')} | {date}")

    return (f"👥 RAPPORT CLIENTS\n{'='*40}\n"
            f"Total clients: {len(customers)}\n"
            f"Actifs: {active} ✅\n"
            f"Inactifs: {inactive} ❌\n\n"
            f"5 derniers clients:\n" + "\n".join(recent_list))

@tool
def admin_stock_report(dummy: str = "") -> str:
    """Rapport complet sur l'état des stocks."""
    products_data = call_api("products", {"display": "[id,name,price,reference]"})
    products = products_data.get("products", [])

    stock_data = call_api("stock_availables", {"display": "[id_product,quantity]"})
    stocks = stock_data.get("stock_availables", [])
    stock_dict = {str(s["id_product"]): int(s["quantity"]) for s in stocks}

    in_stock = []
    out_of_stock = []
    low_stock = []

    for p in products:
        name = extract_text(p.get("name", ""))
        qty = stock_dict.get(str(p["id"]), 0)
        if qty == 0:
            out_of_stock.append(f"  ❌ {name} | Réf:{p.get('reference','')} | 0 unité")
        elif qty <= 5:
            low_stock.append(f"  ⚠️ {name} | Réf:{p.get('reference','')} | {qty} unité(s)")
        else:
            in_stock.append(f"  ✅ {name} | {qty} unité(s)")

    return (f"📦 RAPPORT STOCK\n{'='*40}\n"
            f"En stock: {len(in_stock)} produits\n"
            f"Stock faible (≤5): {len(low_stock)} produits\n"
            f"Rupture: {len(out_of_stock)} produits\n\n"
            f"⚠️ STOCK FAIBLE:\n" + ("\n".join(low_stock) if low_stock else "  Aucun") + "\n\n"
            f"❌ RUPTURE DE STOCK:\n" + ("\n".join(out_of_stock) if out_of_stock else "  Aucun"))