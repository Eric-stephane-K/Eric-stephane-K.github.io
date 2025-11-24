import os
from pathlib import Path
from flask import Blueprint, jsonify, render_template
from .. import limiter
from ..config import BaseConfig
from ..fastspring import retrieve_fastspring_data, get_all_available_products
from ..rag import initialize_vector_db
from langchain_openai import OpenAIEmbeddings

bp = Blueprint('system', __name__)

@bp.route("/status", methods=["GET"])
def status():
    docs_path = BaseConfig.DOCS_PATH
    vector_db_status = "not initialized"
    if os.path.exists(docs_path):
        content_files = list(Path(docs_path).glob("*.md"))
        vector_db_status = f"content available ({len(content_files)} files), not yet initialized"
    vectordb = initialize_vector_db(docs_path, BaseConfig.OPENAI_API_KEY)
    if vectordb:
        vector_db_status = "cached and ready"

    try:
        test = retrieve_fastspring_data({"email": "test@test.com"}, BaseConfig.__dict__)
        if "error" in test and "HTTP 404" in test["error"]:
            fastspring_status = "connected (no test account found - normal)"
        elif "error" not in test:
            fastspring_status = "connected"
        else:
            fastspring_status = f"error: {test['error']}"
    except Exception as e:
        fastspring_status = f"error: {str(e)}"

    try:
        test_embedding = OpenAIEmbeddings(api_key=BaseConfig.OPENAI_API_KEY)
        test_embedding.embed_query("test")
        openai_status = "connected"
    except Exception as e:
        openai_status = f"connection error: {str(e)}"

    try:
        pr = get_all_available_products(BaseConfig.__dict__)
        if "error" not in pr:
            products_count = len(pr.get("products", []))
            products_status = f"connected ({products_count} products available with FastSpring categories)"
            categories = sorted(list(set([p.get('attributes',{}).get('category','Other') for p in pr.get("products", [])])))
            categories_status = f"available ({len(categories)} categories: {', '.join(categories)})"
        else:
            products_status = f"error: {pr['error']}"; categories_status = f"error: {pr['error']}"
    except Exception as e:
        products_status = f"error: {str(e)}"; categories_status = f"error: {str(e)}"

    return jsonify({
        "status": "SECURED PRODUCTION-READY SONGWISH API" if BaseConfig.IS_PRODUCTION else "DEVELOPMENT MODE WITH SECURITY",
        "environment": "production" if BaseConfig.IS_PRODUCTION else "development",
        "cors_enabled": (not BaseConfig.IS_PRODUCTION) or bool(BaseConfig.ALLOWED_ORIGINS),
        "debug_mode": BaseConfig.DEBUG,
        "content_folder": docs_path,
        "vector_db": vector_db_status,
        "fastspring_api": fastspring_status,
        "fastspring_products": products_status,
        "product_categories": categories_status,
        "openai_api": openai_status,
        "auth0_domain": BaseConfig.AUTH0_DOMAIN
    })

@bp.route("/docs", methods=["GET"])
@limiter.limit("50 per minute")
def list_documents():
    docs_path = BaseConfig.DOCS_PATH
    try:
        if not os.path.exists(docs_path):
            return jsonify({"error": f"Documents folder not found: {docs_path}"}), 404
        md_files = [f for f in os.listdir(docs_path) if f.endswith('.md')]
        file_info = []
        for filename in md_files:
            file_path = os.path.join(docs_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_info.append({
                    "filename": filename,
                    "route": __import__('app.constants', fromlist=['ROUTE_MAPPING']).constants.ROUTE_MAPPING.get(filename, "No route mapped"),
                    "size": len(content),
                    "has_mapping": filename in __import__('app.constants', fromlist=['ROUTE_MAPPING']).constants.ROUTE_MAPPING
                })
            except Exception as e:
                file_info.append({"filename": filename, "error": f"Could not read file: {str(e)}"})
        return jsonify({
            "documents_folder": docs_path,
            "total_files": len(md_files),
            "mapped_files": len([f for f in md_files if f in __import__('app.constants', fromlist=['ROUTE_MAPPING']).constants.ROUTE_MAPPING]),
            "files": file_info,
            "route_mappings": __import__('app.constants', fromlist=['ROUTE_MAPPING']).constants.ROUTE_MAPPING
        })
    except Exception as e:
        return jsonify({"error": f"Error listing documents: {str(e)}"}), 500

@bp.route("/", methods=["GET"])
@limiter.limit("20 per minute")
def index():
    return render_template('index.html')
