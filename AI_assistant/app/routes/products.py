from flask import Blueprint, jsonify, request
from .. import limiter
from ..config import BaseConfig
from ..fastspring import get_all_available_products

bp = Blueprint('products', __name__)

@bp.route("/products/categories", methods=["GET","OPTIONS"])
@limiter.limit("100 per minute")
def get_categories():
    if request.method == "OPTIONS" and not BaseConfig.IS_PRODUCTION:
        return jsonify({}), 200
    result = get_all_available_products(BaseConfig.__dict__)
    if "error" in result:
        return jsonify({"error": result["error"]}), 500
    categories = sorted(list(set([p.get('attributes',{}).get('category','Other') for p in result.get("products", [])])))
    return jsonify({"categories": categories, "total": len(categories)}), 200

@bp.route("/products/category/<category_name>", methods=["GET","OPTIONS"])
@limiter.limit("100 per minute")
def get_products_by_category(category_name):
    if request.method == "OPTIONS" and not BaseConfig.IS_PRODUCTION:
        return jsonify({}), 200
    result = get_all_available_products(BaseConfig.__dict__)
    if "error" in result:
        return jsonify({"error": result["error"]}), 500
    filtered = [p for p in result.get("products", []) if p.get('attributes',{}).get('category','Other').lower()==category_name.lower()]
    return jsonify({"products": filtered, "category": category_name, "total": len(filtered)}), 200

@bp.route("/products", methods=["GET","OPTIONS"])
@limiter.limit("100 per minute")
def get_products():
    if request.method == "OPTIONS" and not BaseConfig.IS_PRODUCTION:
        return jsonify({}), 200
    result = get_all_available_products(BaseConfig.__dict__)
    if "error" in result:
        return jsonify({"error": result["error"]}), 500
    return jsonify(result), 200
