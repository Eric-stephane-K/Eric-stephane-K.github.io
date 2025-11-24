import os
from flask import Blueprint, jsonify, request
from .. import limiter
from ..config import BaseConfig
from ..utils import validate_query_input, sanitize_string
from ..security import get_user_email_from_token
from ..fastspring import extract_account_products, get_all_available_products
from ..rag import initialize_vector_db, build_personalized_prompt, extract_cited_sources
from langchain_openai import ChatOpenAI

bp = Blueprint('ai', __name__)

@bp.route("/query", methods=["POST","OPTIONS"])
@limiter.limit("20 per minute" if BaseConfig.IS_PRODUCTION else "100 per minute")
def query():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json(silent=True) or {}
    validation_error = validate_query_input(data)
    if validation_error:
        return jsonify({"error": validation_error}), 400
    user_query = sanitize_string(data["query"], max_length=2000)
    k = data.get("k", 3)
    citations = data.get("citations", False)
    include_products = data.get("include_products", False)

    account_data = ""
    owned_products = []
    customer_info = None

    auth_header = request.headers.get("Authorization")
    if auth_header:
        email = get_user_email_from_token(auth_header, BaseConfig.AUTH0_DOMAIN, "https://api.songwish.ca")
        if email:
            info = extract_account_products(email, BaseConfig.__dict__)
            if "error" not in info:
                account_data = info["account_summary"]
                owned_products = info.get("owned_products", [])
                customer_info = info.get("customer_info", {})

    available_products = []
    if include_products:
        pr = get_all_available_products(BaseConfig.__dict__)
        if "error" not in pr:
            available_products = pr["products"]

    vectordb = initialize_vector_db(BaseConfig.DOCS_PATH, BaseConfig.OPENAI_API_KEY)
    if not vectordb:
        return jsonify({"error": "Vector database not initialized"}), 500

    retriever = vectordb.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(user_query)

    if not docs and not account_data:
        return jsonify({
            "response": "I don't have information about that. Let me check with my team.",
            "sources": [], "query": user_query, "citations_enabled": citations,
            "account_data_used": False, "customer_info": None, "recommended_products": []
        })

    source_to_content = {}
    source_names = []
    for doc in docs:
        src = os.path.basename(doc.metadata.get('source', 'Unknown'))
        if src not in source_to_content:
            source_to_content[src] = []
            source_names.append(src)
        source_to_content[src].append(doc.page_content)

    context_with_sources = ""
    for i, name in enumerate(source_names, 1):
        context_with_sources += f"[Source {i}: {name}]\n" + "\n".join(source_to_content[name]) + "\n\n"

    prompt = build_personalized_prompt(context_with_sources, user_query, available_products, account_data, customer_info)
    llm = ChatOpenAI(model_name="gpt-4", api_key=BaseConfig.OPENAI_API_KEY, temperature=0.1)
    response = llm.invoke(prompt)
    response_text = response.content

    cited_sources = extract_cited_sources(response_text, source_names) if citations else []

    return jsonify({
        "response": response_text, "sources": cited_sources, "query": user_query,
        "citations_enabled": citations, "navigation_enabled": citations,
        "account_data_used": bool(account_data), "customer_info": customer_info or None,
        "recommended_products": []
    })
