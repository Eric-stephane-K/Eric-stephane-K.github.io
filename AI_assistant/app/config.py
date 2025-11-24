import os
import logging

class BaseConfig:
    IS_PRODUCTION = os.getenv('IS_PRODUCTION', 'false').lower() == 'true'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    FASTSPRING_API_USER = os.getenv('FASTSPRING_API_USER', '')
    FASTSPRING_API_PASSWORD = os.getenv('FASTSPRING_API_PASSWORD', '')
    FS_ACCOUNT_ENDPOINT_URL = os.getenv('FS_ACCOUNT_ENDPOINT_URL', 'https://api.fastspring.com/accounts')
    FS_ORDER_ENDPOINT_URL = os.getenv('FS_ORDER_ENDPOINT_URL', 'https://api.fastspring.com/orders')
    FS_PRODUCTS_ENDPOINT_URL = os.getenv('FS_PRODUCTS_ENDPOINT_URL', 'https://api.fastspring.com/products')
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN', 'login.songwish.ca')
    ALLOWED_ORIGINS = [o.strip() for o in os.getenv('ALLOWED_ORIGINS', '').split(',') if o.strip()]
    DOCS_PATH = os.getenv('DOCS_PATH', 'content')

    # Flask
    DEBUG = not IS_PRODUCTION
    TESTING = False

    # Limiter defaults
    DEFAULT_LIMITS_PROD = ["200 per day", "50 per hour"]
    DEFAULT_LIMITS_DEV = ["1000 per hour"]

    @staticmethod
    def configure_logging(is_production: bool):
        if is_production:
            logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s: %(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

