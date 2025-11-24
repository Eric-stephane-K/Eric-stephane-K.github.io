from flask import Blueprint, jsonify, request
from .. import limiter
from ..config import BaseConfig
from ..security import require_auth
from ..fastspring import extract_account_products

bp = Blueprint('account', __name__)

@bp.route("/lookup_account", methods=["POST","OPTIONS"])
@limiter.limit("10 per minute" if BaseConfig.IS_PRODUCTION else "50 per minute")
@require_auth
def lookup_account():
    if request.method == "OPTIONS" and not BaseConfig.IS_PRODUCTION:
        return jsonify({}), 200
    user_email = getattr(request, "user_email", None)
    if not user_email:
        return jsonify({"error": "Authentication required"}), 401
    account_data = extract_account_products(user_email, BaseConfig.__dict__)
    if "error" in account_data:
        return jsonify({"error": account_data["error"]}), 404
    return jsonify(account_data), 200
