import re
from html import escape

def validate_query_input(data):
    if not data or not isinstance(data, dict):
        return "Invalid request format"
    query = (data.get("query") or "").strip()
    if not query:
        return "Query cannot be empty"
    if len(query) > 2000:
        return "Query too long (max 2000 characters)"
    dangerous = ['<script', 'javascript:', 'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET', '<iframe', 'eval(', 'document.cookie']
    ql = query.lower()
    if any(x.lower() in ql for x in dangerous):
        return "Invalid query content detected"
    if len(re.findall(r'[<>"\';{}]', query)) > 10:
        return "Query contains too many special characters"
    return None

def sanitize_string(text, max_length=1000):
    if not text:
        return ""
    text = str(text)[:max_length]
    text = escape(text).replace('\x00', '')
    return text.strip()
