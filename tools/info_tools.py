import requests
import os
import re
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PRESTASHOP_URL")
WS_KEY = os.getenv("PRESTASHOP_WS_KEY")

# Mapping des id de langue PrestaShop (à adapter selon ta config réelle)
LANG_ID_MAP = {
    "1": "de",
    "2": "en",
    "3": "fr"
}

def call_api(endpoint, params={}):
    base_params = {
        "ws_key": WS_KEY,
        "output_format": "JSON"
    }
    response = requests.get(f"{BASE_URL}/api/{endpoint}", params={**base_params, **params})
    return response.json()

def extract_text(field, lang_id=None):
    """Extrait le texte d'un champ multilingue PrestaShop.
    Format réel: [{'id': '1', 'value': '...'}, {'id': '2', 'value': '...'}]
    """
    if isinstance(field, list):
        if lang_id:
            for item in field:
                if str(item.get("id")) == str(lang_id):
                    return item.get("value", "")
        return field[0].get("value", "") if field else ""
    elif isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""

@tool
def get_all_info_pages(dummy: str = "") -> str:
    """Retourne la liste de toutes les pages d'information disponibles (à propos, contact, CGV, FAQ, etc.)."""
    data = call_api("content_management_system", {"display": "[id,meta_title]"})
    pages = data.get("content_management_system", [])
    if not pages:
        return "Aucune page d'information trouvée."
    result = []
    for p in pages:
        title = extract_text(p.get("meta_title", ""))
        result.append(f"- {title} (ID: {p['id']})")
    return "\n".join(result)

@tool
def get_info_page_content(page_topic: str) -> str:
    """Récupère le contenu d'une page d'information spécifique (ex: 'Impressum', 'Datenschutz', 'AGB', 'Über uns', 'Sichere Zahlung', 'contact', 'à propos', 'CGV', 'paiement')."""
    data = call_api("content_management_system", {"display": "[id,meta_title,content]"})
    pages = data.get("content_management_system", [])
    if not pages:
        return "Aucune page d'information trouvée."

    matched = None
    for p in pages:
        # On vérifie le titre dans toutes les langues disponibles
        title_field = p.get("meta_title", "")
        if isinstance(title_field, list):
            titles = [item.get("value", "") for item in title_field]
        else:
            titles = [extract_text(title_field)]

        if any(page_topic.lower() in t.lower() for t in titles):
            matched = p
            break

    if not matched:
        all_titles = []
        for p in pages:
            title_field = p.get("meta_title", "")
            if isinstance(title_field, list):
                all_titles.extend([item.get("value", "") for item in title_field])
        return f"Page non trouvée pour '{page_topic}'. Pages disponibles: {', '.join(set(all_titles))}"

    content = extract_text(matched.get("content", ""))
    clean_content = re.sub('<[^<]+?>', ' ', content)
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()

    return clean_content[:2000] if clean_content else "Cette page ne contient pas encore de contenu."