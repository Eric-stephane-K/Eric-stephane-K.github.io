import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import BaseConfig
from .security import https_enforcement, security_headers, request_logging

# global limiter for decorators
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per hour"], storage_uri="memory://")

def create_app():
    BaseConfig.configure_logging(BaseConfig.IS_PRODUCTION)
    logger = logging.getLogger(__name__)

    app = Flask(__name__, template_folder="../templates")
    # load config values into app.config
    app.config.from_object(BaseConfig)
    app.config['DEBUG'] = BaseConfig.DEBUG

    # CORS
    if not BaseConfig.IS_PRODUCTION:
        CORS(app)
        logger.info("DEVELOPMENT: CORS enabled for all origins")
    else:
        if BaseConfig.ALLOWED_ORIGINS:
            CORS(app, origins=BaseConfig.ALLOWED_ORIGINS)
            logger.warning(f"PRODUCTION: CORS enabled for specific origins: {BaseConfig.ALLOWED_ORIGINS}")
        else:
            logger.warning("PRODUCTION: CORS disabled - same-origin only")

    # Security hooks
    if BaseConfig.IS_PRODUCTION:
        https_enforcement(app)
        security_headers(app)
        request_logging(app, logger)

    # Limiter
    default_limits = BaseConfig.DEFAULT_LIMITS_PROD if BaseConfig.IS_PRODUCTION else BaseConfig.DEFAULT_LIMITS_DEV
    limiter._default_limits = default_limits  # update default
    limiter.init_app(app)

    # Blueprints
    from .routes.products import bp as products_bp
    from .routes.account import bp as account_bp
    from .routes.ai import bp as ai_bp
    from .routes.system import bp as system_bp
    app.register_blueprint(products_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(system_bp)

    return app
