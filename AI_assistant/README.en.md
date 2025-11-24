# SongWish API — Modular Architecture (Flask)

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

> E‑commerce + RAG/LLM API for SongWish, organized with **horizontal domain modularization** (config, security, FastSpring, RAG/AI, routes).

![Architecture](./architecture.png)

---

## 🚀 Overview

- **Flask app factory** with domain-oriented Blueprints
- **FastSpring** integration (catalog, accounts, orders)
- **RAG** (Chroma + OpenAI embeddings) over Markdown docs (`content/*.md`)
- **Auth0 JWT** user authentication
- **Rate limiting** via `flask-limiter`
- **CORS** configurable (restricted origins in production)

---

## 🧭 Project layout

```
songwish_api_mod/
├─ README.md                 # French
├─ README.en.md              # English (this file)
├─ requirements.txt
├─ run.py
├─ architecture.png
├─ architecture.svg
├─ templates/
│  └─ index.html
└─ app/
   ├─ __init__.py
   ├─ config.py
   ├─ constants.py
   ├─ utils.py
   ├─ security.py
   ├─ fastspring.py
   ├─ rag.py
   └─ routes/
      ├─ __init__.py
      ├─ products.py
      ├─ account.py
      ├─ ai.py
      └─ system.py
```

---

## 🔐 Environment variables

| Variable | Description | Default |
|---|---|---|
| `IS_PRODUCTION` | Enables prod constraints (HTTPS, headers, CORS restrictions, tighter limits) | `false` |
| `OPENAI_API_KEY` | OpenAI key for embeddings/LLM | — |
| `FASTSPRING_API_USER` | FastSpring API username | — |
| `FASTSPRING_API_PASSWORD` | FastSpring API password | — |
| `FS_ACCOUNT_ENDPOINT_URL` | Accounts endpoint | `https://api.fastspring.com/accounts` |
| `FS_ORDER_ENDPOINT_URL` | Orders endpoint | `https://api.fastspring.com/orders` |
| `FS_PRODUCTS_ENDPOINT_URL` | Products endpoint | `https://api.fastspring.com/products` |
| `AUTH0_DOMAIN` | Auth0 domain (e.g. `login.songwish.ca`) | `login.songwish.ca` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed origins (prod) | empty (= same-origin) |
| `DOCS_PATH` | Markdown folder for RAG | `content` |

> In production, CORS is **off by default** (same-origin) unless `ALLOWED_ORIGINS` is set.

---

## ▶️ Run

**Development**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export IS_PRODUCTION=false
python run.py
```

**Production** (Gunicorn example)

```bash
export IS_PRODUCTION=true
export ALLOWED_ORIGINS=https://songwish.ca,https://www.songwish.ca
gunicorn -w 4 -b 0.0.0.0:8000 'run:app'
```

Front with a reverse proxy (Nginx/Caddy) that terminates TLS and forwards `X-Forwarded-Proto` for HTTPS enforcement.

---

## 🔗 Key endpoints

- `GET /status` — system health (FastSpring/OpenAI/RAG)
- `GET /docs` — list Markdown docs (`DOCS_PATH`)
- `GET /` — simple index page (HTML)
- `GET /products` — aggregated catalog with pricing/discounts
- `GET /products/categories` — categories
- `GET /products/category/<name>` — products by category
- `POST /lookup_account` — account + purchase history (JWT required)
- `POST /query` — question over Markdown base + optional personalization  
  Example body:
  ```json
  {"query":"How to install reMIDI 4?","k":3,"citations":true,"include_products":true}
  ```

---

## 🔑 Auth (Auth0)

- Protected endpoints use **RS256 JWT**, validated against the **JWKS** from `AUTH0_DOMAIN`.
- Expected API audience: `https://api.songwish.ca` (adjust as needed).
- See `app/security.py` (`require_auth` injects `request.user_email`).

---

## 🧠 RAG

- Vector store (**Chroma**) lazy-initialized on first use (in-memory cache).
- Markdown documents from `DOCS_PATH` are enriched with route metadata from `constants.ROUTE_MAPPING`, split by headers/sections.
- Prompt includes: navigation routes, available products (if `include_products=true`), and customer data (if authenticated).

If `DOCS_PATH` is empty, a `scripts/fetch_docs.py` script is expected to fetch content (e.g., from S3).

---

## ✅ CI/CD — GitHub Actions

This repository includes a **CI workflow** that:
- Lints Python sources with **flake8**
- Runs unit tests with **pytest**
- Caches pip dependencies for faster builds

**Badge** (replace `OWNER` and `REPO` with your GitHub org/repo):
```md
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
```

---

## 📄 License

© SongWish Inc. All rights reserved.
