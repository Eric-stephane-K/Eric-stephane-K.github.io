# SongWish API — Architecture modulaire (Flask)

> API e‑commerce + RAG/LLM pour SongWish, organisée en **modularisation horizontale par domaine** (config, sécurité, FastSpring, RAG/AI, routes).

![Architecture](./architecture.png)

---

## 🚀 Aperçu

- **Flask app factory** avec Blueprints par domaine
- **FastSpring** (catalogue, comptes, commandes)
- **RAG** (Chroma + OpenAI embeddings) sur la doc Markdown (`content/*.md`)
- **Auth0 JWT** pour l’auth utilisateur
- **Rate limiting** via `flask-limiter`
- **CORS** configurable (origines restreintes en prod)

---

## 🧭 Arborescence

```
songwish_api_mod/
├─ README.md
├─ requirements.txt
├─ run.py
├─ architecture.png
├─ architecture.svg
├─ templates/
│  └─ index.html
└─ app/
   ├─ __init__.py          # App factory, CORS, security hooks, limiter, enregistrement des blueprints
   ├─ config.py            # Configuration centralisée (prod/dev, clés API, CORS, logging)
   ├─ constants.py         # ROUTE_MAPPING + descriptions des routes
   ├─ utils.py             # Validation/sanitation entrée utilisateur
   ├─ security.py          # HTTPS, headers, logs, Auth0 (JWT), @require_auth
   ├─ fastspring.py        # Intégrations FastSpring (catalogue, comptes, commandes)
   ├─ rag.py               # Init vectordb, split markdown, prompt personnalisé, citations
   └─ routes/
      ├─ __init__.py
      ├─ products.py       # /products, /products/categories, /products/category/<name>
      ├─ account.py        # /lookup_account (JWT requis)
      ├─ ai.py             # /query (RAG + LLM)
      └─ system.py         # /status, /docs, index
```

---

## 🧩 Dépendances

Voir **requirements.txt** (Flask, Flask-Cors, Flask-Limiter, LangChain Community/OpenAI, ChromaDB, PyJWT, Requests, Markdown).

Installation locale :

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

---

## 🔐 Variables d’environnement

| Variable | Description | Par défaut |
|---|---|---|
| `IS_PRODUCTION` | Active les contraintes de prod (HTTPS forcé, headers, CORS restreint, limites) | `false` |
| `OPENAI_API_KEY` | Clé OpenAI pour embeddings/LLM | — |
| `FASTSPRING_API_USER` | Identifiant API FastSpring | — |
| `FASTSPRING_API_PASSWORD` | Mot de passe API FastSpring | — |
| `FS_ACCOUNT_ENDPOINT_URL` | Endpoint comptes | `https://api.fastspring.com/accounts` |
| `FS_ORDER_ENDPOINT_URL` | Endpoint commandes | `https://api.fastspring.com/orders` |
| `FS_PRODUCTS_ENDPOINT_URL` | Endpoint produits | `https://api.fastspring.com/products` |
| `AUTH0_DOMAIN` | Domaine Auth0 (ex. `login.songwish.ca`) | `login.songwish.ca` |
| `ALLOWED_ORIGINS` | Liste d’origines autorisées (prod), séparées par des virgules | vide (= same-origin) |
| `DOCS_PATH` | Dossier Markdown pour RAG | `content` |

> **Note**: en prod, CORS est **désactivé** par défaut (same‑origin) si `ALLOWED_ORIGINS` est vide.

---

## ▶️ Lancer le serveur

**Développement** :

```bash
export IS_PRODUCTION=false
python run.py
# http://localhost:5000
```

**Production** (exemple Gunicorn) :

```bash
export IS_PRODUCTION=true
export ALLOWED_ORIGINS=https://songwish.ca,https://www.songwish.ca
gunicorn -w 4 -b 0.0.0.0:8000 'run:app'
```

Placez un reverse proxy (Nginx/Caddy) en frontal qui termine TLS et propage `X-Forwarded-Proto` pour l’enforcement HTTPS.

---

## 🔗 Endpoints principaux

### Système
- `GET /status` — santé du système (FastSpring/OpenAI/RAG)
- `GET /docs` — inventaire des fichiers Markdown (`DOCS_PATH`)
- `GET /` — page d’accueil simple (HTML)

### Produits (FastSpring)
- `GET /products` — catalogue agrégé + prix/remises
- `GET /products/categories` — catégories disponibles
- `GET /products/category/<name>` — produits filtrés par catégorie

### Compte (Auth requis)
- `POST /lookup_account` — informations client + historique d’achats  
  **Headers** : `Authorization: Bearer <JWT>`

### Assistant (RAG/LLM)
- `POST /query` — question sur la base Markdown + (optionnel) personnalisation par compte et produits  
  **Body JSON** :
  ```json
  {
    "query": "Comment installer reMIDI 4 ?",
    "k": 3,
    "citations": true,
    "include_products": true
  }
  ```

---

## 🔑 Authentification (Auth0)

- Les endpoints protégés utilisent un **JWT RS256** validé contre le **JWKS** d’`AUTH0_DOMAIN`.
- Audience attendue côté API : `https://api.songwish.ca` (adapter si nécessaire).
- Décodage/verif dans `app/security.py` → `require_auth` ajoute `request.user_email`.

---

## 🧠 RAG & contenu

- Le vecteur store **Chroma** est initialisé au premier appel (cache mémoire).
- Les fichiers Markdown du dossier `DOCS_PATH` sont enrichis avec des métadonnées de route (`constants.ROUTE_MAPPING`), découpés par titres/sections.
- Le prompt intègre : routes de navigation, produits disponibles (si `include_products=true`), et données client (si authentifié).

> Si `DOCS_PATH` est vide, un script `scripts/fetch_docs.py` est attendu pour rapatrier la doc (S3, etc.).

---

## 🛡️ Sécurité

- **Production** : redirection HTTPS, headers de protection (HSTS, X-Content-Type-Options, X-Frame-Options, …).
- **Rate limiting** (`flask-limiter`) :
  - Dev : `1000/hour` par défaut
  - Prod : `200/day` et `50/hour` (et overrides sur certaines routes)
- **CORS** : désactivé par défaut en prod (same‑origin). Spécifier `ALLOWED_ORIGINS` pour l’ouvrir.

---

## 🧪 Tests (piste rapide)

- Ajouter **pytest** & **pytest-flask**
- Doubler les appels FastSpring/OpenAI avec **factories**/mocks
- Exposer des **schemas Pydantic** pour stabiliser les réponses JSON
- Tests de charge ciblés sur `/query` et `/products`

---

## 🛫 Déploiement

- **Gunicorn** + **Nginx** (TLS, GZip, caching statique)
- Variables d’env injectées via système (K8s, Docker secrets, etc.)
- Healthcheck `GET /status` pour readiness/liveness

---

## 📄 Licence

© SongWish Inc. Tous droits réservés.
