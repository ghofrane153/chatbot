# Chatbot IA e-commerce 

Système de deux assistants conversationnels connectés à une boutique :

- un **chatbot client** multilingue (français, anglais, allemand) qui répond aux questions sur les produits, les stocks, les catégories et les informations de la boutique ;
- un **assistant administrateur** qui consulte et modifie les données de la boutique (produits, stocks, commandes, clients, rapports), avec **validation humaine obligatoire** avant toute modification.

Projet réalisé dans le cadre d'un stage (juin – août 2026).

<!-- Ajouter une capture ou un GIF du widget de chat : docs/demo.gif -->

## Fonctionnalités

### Chatbot client
- Recherche de produits par nom ou référence, filtre par prix, produits les moins chers / les plus chers
- Vérification des stocks, produits disponibles ou en rupture
- Navigation par catégories
- **Recommandations** : à partir d'un besoin exprimé librement, l'agent parcourt le catalogue et propose 2 à 4 produits adaptés, en cherchant des mots-clés dans plusieurs langues
- Réponses sur les pages d'information de la boutique (mentions légales, CGV, paiement sécurisé…) à partir du contenu réel, sans inventer
- Détection automatique de la langue du client et réponse dans la même langue

### Assistant administrateur
- **Produits** : recherche, consultation, modification du prix, activation / désactivation
- **Stocks** : consultation, mise à jour, ajout, alerte sur les stocks faibles
- **Commandes** : liste, filtre par statut, détail, commandes en attente, changement de statut
- **Clients** : recherche, détail, nombre de commandes, activation / désactivation
- **Rapports** : rapport global, chiffre d'affaires, clients, stocks
- **Human-in-the-Loop** : toute action qui modifie la boutique est mise en pause avant exécution ; l'administrateur voit l'action et ses paramètres, puis confirme ou annule
- Accès protégé par jeton (Bearer token) et journal des actions

### Fiabilité et sécurité
- **Guardrails en entrée** : un LLM classifie chaque message et bloque les tentatives d'injection de prompt, les demandes de données sensibles, les contenus dangereux et les questions hors sujet
- **Guardrails en sortie** : détection des fuites du prompt système et nettoyage des réponses
- **Fallback multi-fournisseurs** : si un fournisseur de LLM atteint sa limite de requêtes, l'agent bascule automatiquement sur le suivant (Groq → Gemini → OpenRouter → Mistral)
- **Cache sémantique** : les questions proches d'une question déjà posée (similarité cosinus ≥ 0,95 entre embeddings `all-MiniLM-L6-v2`) reçoivent directement la réponse en cache, ce qui réduit la latence et le nombre d'appels au LLM

## Architecture

```
  Widget client (React)                    Interface admin (React)
          │                                         │
          ▼                                         ▼
  API client  (FastAPI)                    API admin  (FastAPI, port 8002)
   │  guardrails entrée                     │  authentification par jeton
   │  cache sémantique                      │  agent LangGraph
   │  agent LangGraph (ReAct)               │   ├─ lecture  → exécution directe
   │  guardrails sortie                     │   └─ écriture → pause + confirmation (HITL)
   ▼                                        ▼
  Outils lecture (produits, stocks,       Outils admin (produits, stocks,
  catégories, pages d'info)               commandes, clients, rapports)
          └──────────────┬─────────────────────────┘
                         ▼
               API Webservice PrestaShop
```

## Structure du projet

```
chatbot/
├── agent/chatbot_agent.py       # Agent client : prompt, fallback multi-LLM
├── tools/                       # Outils client : produits, stocks, catégories, pages d'info
├── guardrails/                  # Vérification des entrées et des sorties
├── cache/semantic_cache.py      # Cache sémantique par embeddings
├── api/server.py                # API FastAPI du chatbot client
├── admin/
│   ├── agent/admin_agent.py     # Agent admin avec Human-in-the-Loop
│   ├── tools/                   # Outils admin : produits, stocks, commandes, clients, rapports
│   └── api/admin_server.py      # API FastAPI admin
├── frontend/                    # Widget de chat client (React + Vite)
├── admin_frontend/              # Interface de chat admin (React + Vite)
├── main.py                      # Version console du chatbot
├── start.py                     # Point d'entrée de l'API client
└── Dockerfile
```

## Technologies

| Domaine | Outils |
|---|---|
| Agents IA | LangChain, LangGraph (agents ReAct, checkpoints, interruption avant exécution) |
| LLM | Groq (Llama 3.1), Google Gemini, OpenRouter, Mistral |
| Embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`) |
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React, Vite |
| E-commerce | API Webservice PrestaShop |
| Déploiement | Docker |

## Installation et lancement

**Prérequis :** Python 3.11+, Node.js 18+, une boutique PrestaShop avec le Webservice activé, au moins une clé API de LLM (Groq recommandé).

### 1. Configuration

Créer un fichier `.env` à la racine :

```env
# Boutique PrestaShop
PRESTASHOP_URL=https://votre-boutique.com
PRESTASHOP_WS_KEY=votre_cle_webservice

# Fournisseurs LLM (au moins un)
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
MISTRAL_API_KEY=

# Accès administrateur
ADMIN_SECRET_TOKEN=un_jeton_long_et_secret

# Optionnel : désactiver le cache sémantique
DISABLE_SEMANTIC_CACHE=false
```

### 2. Backend

```bash
pip install -r requirements.txt

# API du chatbot client (port 8080 par défaut)
python start.py

# API de l'assistant admin (dans un second terminal)
uvicorn admin.api.admin_server:app --port 8002
```

Pour tester le chatbot directement dans le terminal : `python main.py`.

### 3. Frontend

```bash
# Widget client
cd frontend && npm install && npm run dev

# Interface admin (dans un autre terminal)
cd admin_frontend && npm install && npm run dev
```

## Exemples

**Client**
- *Avez-vous des bouteilles isothermes ?*
- *Quels sont vos produits à moins de 20 € ?*
- *Je cherche une idée de cadeau.*
- *Quels moyens de paiement acceptez-vous ?*

**Administrateur**
- *Quels produits ont un stock inférieur à 5 ?*
- *Génère un rapport du chiffre d'affaires.*
- *Passe la commande 42 au statut expédiée.* → demande de confirmation avant exécution

## Auteure

**Ghofrane Kerkeni** — élève-ingénieure en informatique à l'ESIGELEC
[LinkedIn](https://www.linkedin.com/in/VOTRE-PROFIL) · [GitHub](https://github.com/ghofrane153)
