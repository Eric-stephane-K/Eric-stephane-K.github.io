import json
import logging
import requests
import jwt
from functools import wraps
from flask import request, jsonify, redirect, current_app

logger = logging.getLogger(__name__)

def https_enforcement(app):
    @app.before_request
    def force_https():
        if app.config.get('IS_PRODUCTION') and request.headers.get('X-Forwarded-Proto') != 'https':
            return redirect(request.url.replace('http://', 'https://'), code=301)

def security_headers(app):
    @app.after_request
    def add_security_headers(response):
        if app.config.get('IS_PRODUCTION'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

def request_logging(app, logger):
    @app.before_request
    def log_request_info():
        if not app.config.get('IS_PRODUCTION'):
            return
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if any(w in (user_agent or '').lower() for w in ['bot', 'crawler', 'scanner']):
            logger.warning(f"Bot request from {ip_address}: {user_agent}")
        if request.endpoint in ['account.lookup_account', 'ai.query'] and request.method == 'POST':
            logger.info(f"API request to {request.endpoint} from {ip_address}")

def get_public_key(token, auth0_domain: str):
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        jwks_url = f'https://{auth0_domain}/.well-known/jwks.json'
        response = requests.get(jwks_url, timeout=15)
        jwks = response.json()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        return None
    except Exception as e:
        logger.error(f"Failed to get public key: {e}")
        return None

def get_user_email_from_token(auth_header, auth0_domain: str, audience: str):
    if not auth_header:
        return None
    try:
        token = auth_header.replace("Bearer ", "")
        key = get_public_key(token, auth0_domain)
        if not key:
            logger.error("Could not get public key for token")
            return None
        payload = jwt.decode(token, key, algorithms=["RS256"], audience=audience)
        return payload.get("email")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired"); return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}"); return None
    except Exception as e:
        logger.error(f"Token verification error: {e}"); return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return jsonify({}), 200
        auth_header = request.headers.get("Authorization")
        email = get_user_email_from_token(auth_header, current_app.config['AUTH0_DOMAIN'], "https://api.songwish.ca")
        if not email:
            return jsonify({"error": "Authentication required"}), 401
        request.user_email = email
        return f(*args, **kwargs)
    return decorated
