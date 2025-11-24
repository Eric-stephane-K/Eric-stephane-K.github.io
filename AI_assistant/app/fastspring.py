import os
import logging
from datetime import datetime
from urllib.parse import unquote
import requests

logger = logging.getLogger(__name__)

def retrieve_fastspring_data(params, cfg):
    headers = {"accept": "application/json","User-Agent": "SongWish-API/1.0"}
    FS_ACCOUNT_ENDPOINT_URL = cfg['FS_ACCOUNT_ENDPOINT_URL']
    FS_ORDER_ENDPOINT_URL = cfg['FS_ORDER_ENDPOINT_URL']
    if not params:
        url = FS_ACCOUNT_ENDPOINT_URL
    elif len(params)==1:
        (raw_key, value) = list(params.items())[0]
        value = unquote((value or '').strip())
        key = 'orders' if raw_key.lower()=='order' else raw_key.lower()
        if key == "orders":
            url = f"{FS_ORDER_ENDPOINT_URL}/{value}"
        elif key == "email":
            url = f"{FS_ACCOUNT_ENDPOINT_URL}?email={value}"
        elif key in ["accountid", "account"]:
            url = f"{FS_ACCOUNT_ENDPOINT_URL}/{value}"
        else:
            url = f"{FS_ACCOUNT_ENDPOINT_URL}/{value}"
    else:
        url = FS_ACCOUNT_ENDPOINT_URL

    try:
        r = requests.get(url, auth=(cfg['FASTSPRING_API_USER'], cfg['FASTSPRING_API_PASSWORD']), headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return {"error": f"Not found: {url}"}
        logger.error(f"FastSpring API error {r.status_code}: {r.text}")
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out - FastSpring API may be slow"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection error: Unable to reach FastSpring API"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def extract_language_content(data, preferred_lang='en'):
    if not data:
        return ""
    if isinstance(data, dict):
        if preferred_lang in data:
            return data[preferred_lang]
        if 'default' in data:
            return data['default']
        if data:
            return list(data.values())[0]
        return ""
    return str(data)

def get_product_category(product_details: dict) -> str:
    return product_details.get('attributes', {}).get('category', 'Other')

def is_product_free(product_path: str, price_value: float) -> bool:
    return (price_value == 0.0 or any(x in (product_path or '').lower() for x in ['trial','free']))

def get_product_tags(product_details: dict, product_path: str, price_value: float) -> list:
    tags = []
    category = get_product_category(product_details)
    tags.append(category.lower().replace(' ', '-'))
    if is_product_free(product_path, price_value):
        tags.append('trial' if 'trial' in (product_path or '').lower() else 'free')
    else:
        tags.append('paid')
    pl = (product_path or '').lower()
    if 'remidi' in pl:
        tags += ['midi-sampler', 'vst']
    elif 'rechannel' in pl:
        tags += ['midi-effect', 'vst']
    elif 'jazz' in pl:
        tags += ['jazz', 'midi-files']
    elif 'sample-loops' in pl:
        tags += ['loops', 'samples']
    return tags

def get_all_available_products(cfg):
    try:
        headers = {"accept": "application/json","User-Agent": "SongWish-API/1.0"}
        resp = requests.get(cfg['FS_PRODUCTS_ENDPOINT_URL'], auth=(cfg['FASTSPRING_API_USER'], cfg['FASTSPRING_API_PASSWORD']), headers=headers, timeout=30)
        if resp.status_code != 200:
            return {"error": f"Failed to fetch catalog: HTTP {resp.status_code}"}
        product_ids = resp.json().get("products", [])
        if not product_ids:
            return {"error": "No products found in catalog"}
        products = []
        for product_id in product_ids:
            try:
                pr = requests.get(f"{cfg['FS_PRODUCTS_ENDPOINT_URL']}/{product_id}", auth=(cfg['FASTSPRING_API_USER'], cfg['FASTSPRING_API_PASSWORD']), headers=headers, timeout=30)
                if pr.status_code != 200:
                    continue
                pdata = pr.json()
                if 'products' in pdata and pdata['products']:
                    details = pdata['products'][0]
                    display = extract_language_content(details.get("display", {}), 'en') or product_id.replace('-', ' ').title()
                    pricing = details.get("pricing", {}).get("price", {})
                    usd_price = pricing.get('USD', 0) if isinstance(pricing, dict) else 0
                    description_data = details.get("description", {})
                    summary = extract_language_content(description_data.get("summary", {}), 'en')
                    product_path = details.get("product", product_id)
                    category = get_product_category(details)
                    tags = get_product_tags(details, product_path, usd_price)
                    is_free = is_product_free(product_path, usd_price)
                    download = details.get("attributes", {}).get("download", "")
                    formatted = {
                        "path": product_path,
                        "image": details.get("image", "/api/placeholder/200/120"),
                        "display": display,
                        "price": f"${usd_price:.2f}",
                        "total": f"${usd_price:.2f}",
                        "priceValue": usd_price,
                        "description": {"summary": summary},
                        "discount": None,
                        "discountPercent": None,
                        "attributes": {"category": category, "download": download},
                        "categories": [category],
                        "tags": tags,
                        "active": True,
                        "available": True,
                        "trial": 'trial' in (product_path or '').lower(),
                        "subscription": False,
                        "sku": details.get("sku", product_id),
                        "is_free": is_free
                    }
                    discount = details.get("pricing", {}).get("discount")
                    if discount:
                        pct = discount.get("percentage", 0)
                        formatted["discount"] = {"reason": discount.get("reason", "")}
                        formatted["discountPercent"] = f"{pct}%"
                        final = usd_price - (usd_price * (pct/100))
                        formatted["total"] = f"${final:.2f}"
                        formatted["priceValue"] = final
                    products.append(formatted)
            except Exception as e:
                logger.error(f"Error fetching product {product_id}: {e}")
                continue
        return {"products": products}
    except Exception as e:
        return {"error": f"Failed to fetch catalog: {str(e)}"}

def extract_account_products(email, cfg, retrieve_fn=retrieve_fastspring_data):
    try:
        account_data = retrieve_fn({"email": email}, cfg)
        if "error" in account_data:
            return {"error": account_data["error"]}
        accounts = account_data.get("accounts", [])
        if not accounts:
            return {"error": "No account found for this email address"}
        result = {
            "customer_info": {},
            "orders": [],
            "total_orders": 0,
            "total_products": 0,
            "total_files": 0,
            "total_licenses": 0,
            "account_summary": "",
            "owned_products": []
        }
        order_info_map = {}
        for account in accounts:
            if not result["customer_info"]:
                contact = account.get("contact", {})
                address = account.get("address", {})
                result["customer_info"] = {
                    "account_id": account.get("account", "N/A"),
                    "email": contact.get("email", email),
                    "first_name": contact.get("first", "N/A"),
                    "last_name": contact.get("last", "N/A"),
                    "full_name": f"{contact.get('first','')} {contact.get('last','')}".strip(),
                    "country": account.get("country", "N/A"),
                    "city": address.get("city", "N/A"),
                    "region": address.get("region", "N/A"),
                    "postal_code": address.get("postalCode", "N/A")
                }
            charges = account.get("charges", [])
            for charge in charges:
                if "order" in charge:
                    order_info_map[charge["order"]] = {
                        "date": charge.get("timestampDisplay", "N/A"),
                        "utc_timestamp": charge.get("timestamp", 0),
                        "reference": charge.get("orderReference", "N/A"),
                        "total": charge.get("total", 0),
                        "currency": charge.get("currency", "USD"),
                        "status": charge.get("status", "unknown")
                    }
            for order_id in account.get("orders", []):
                od = retrieve_fn({"orders": order_id}, cfg)
                if "error" in od:
                    continue
                info = order_info_map.get(order_id, {})
                utc_date = "N/A"
                if info.get("utc_timestamp"):
                    try:
                        from datetime import datetime
                        utc_date = datetime.utcfromtimestamp(info["utc_timestamp"]/1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                    except:
                        pass
                order_data = {
                    "order_id": order_id,
                    "order_reference": info.get("reference","N/A"),
                    "date": info.get("date","N/A"),
                    "utc_date": utc_date,
                    "total": info.get("total",0),
                    "currency": info.get("currency","USD"),
                    "status": info.get("status","unknown"),
                    "products": [],
                    "files": [],
                    "licenses": []
                }
                for item in od.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    subtotal = item.get("subtotal", 0)
                    product = {
                        "display": item.get("display","N/A"),
                        "product_id": item.get("product","N/A"),
                        "quantity": item.get("quantity",1),
                        "coupon": item.get("coupon","N/A"),
                        "subtotal": subtotal,
                        "subtotal_display": item.get("subtotalDisplay", f"${subtotal:.2f}"),
                        "sku": item.get("sku","N/A")
                    }
                    order_data["products"].append(product)
                    owned_product = {
                        "path": item.get("product","N/A"),
                        "display": item.get("display","N/A"),
                        "purchaseDate": info.get("date","N/A"),
                        "orderId": order_id,
                        "orderReference": info.get("reference","N/A"),
                        "price": subtotal,
                        "price_display": item.get("subtotalDisplay", f"${subtotal:.2f}"),
                        "currency": info.get("currency","USD"),
                        "sku": item.get("sku","N/A")
                    }
                    result["owned_products"].append(owned_product)
                    fulfillments = item.get("fulfillments", {})
                    for fk, fv in fulfillments.items():
                        if fk == "instructions":
                            continue
                        if isinstance(fv, list):
                            for it in fv:
                                if not isinstance(it, dict):
                                    continue
                                ftype = it.get("type","")
                                if ftype == "file" and "file" in it:
                                    size = it.get("size",0)
                                    order_data["files"].append({
                                        "display": it.get("display","N/A"),
                                        "file_url": it.get("file","N/A"),
                                        "product": product["display"],
                                        "product_id": product["product_id"],
                                        "size": size,
                                        "size_mb": round(size/(1024*1024),1),
                                        "type": ftype,
                                        "fulfillment_key": fk
                                    })
                                elif ftype == "license" and "license" in it:
                                    order_data["licenses"].append({
                                        "display": it.get("display","N/A"),
                                        "license_key": it.get("license","N/A"),
                                        "product": product["display"],
                                        "product_id": product["product_id"],
                                        "type": ftype,
                                        "fulfillment_key": fk
                                    })
                result["orders"].append(order_data)
        result["total_orders"] = len(result["orders"])
        result["total_products"] = sum(len(o["products"]) for o in result["orders"])
        result["total_files"] = sum(len(o["files"]) for o in result["orders"])
        result["total_licenses"] = sum(len(o["licenses"]) for o in result["orders"])

        c = result["customer_info"]
        summary = [f"CUSTOMER ACCOUNT INFORMATION FOR {c['full_name']} ({c['email']}):",
                   "", "Customer Details:",
                   f"- Account ID: {c['account_id']}",
                   f"- Name: {c['full_name']}", f"- Email: {c['email']}",
                   f"- Location: {c['city']}, {c['region']}, {c['country']}", "",
                   "Account Summary:",
                   f"- Total Orders: {result['total_orders']}",
                   f"- Total Products Purchased: {result['total_products']}",
                   f"- Total Download Files: {result['total_files']}",
                   f"- Total License Keys: {result['total_licenses']}", "", "PURCHASE HISTORY:" ]
        for order in result["orders"]:
            total_mb = sum([f['size_mb'] for f in order['files']])
            summary += ["",
                        f"Order #{order['order_reference']} (ID: {order['order_id']}):",
                        f"- Date: {order['date']}",
                        f"- Total: {order['currency']} {order['total']}",
                        f"- Status: {order['status']}",
                        f"- Products: {', '.join([f"{p['display']} ({p['subtotal_display']})" for p in order['products']])}",
                        f"- Downloads: {len(order['files'])} files available ({total_mb} MB total)",
                        f"- License Keys: {len(order['licenses'])} keys issued"]
        result["account_summary"] = "\n".join(summary)
        return result
    except Exception as e:
        return {"error": f"Failed to extract account data: {str(e)}"}
