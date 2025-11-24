import os
import logging
import subprocess
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import MarkdownTextSplitter, MarkdownHeaderTextSplitter
from langchain.schema.document import Document
from .constants import ROUTE_MAPPING, get_all_route_mappings

logger = logging.getLogger(__name__)

_vector_db_cache = None

def initialize_vector_db(docs_path: str, openai_api_key: str):
    global _vector_db_cache
    if _vector_db_cache:
        return _vector_db_cache
    if not os.path.exists(docs_path):
        os.makedirs(docs_path, exist_ok=True)
        logger.info(f"Created content directory: {docs_path}")
    if not os.listdir(docs_path):
        try:
            result = subprocess.run(["python", "scripts/fetch_docs.py"], capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to fetch content from S3: {result.stderr}")
                return None
            logger.info("Successfully fetched content from S3")
        except Exception as e:
            logger.error(f"S3 content fetch error: {e}")
            return None
    loader = DirectoryLoader(docs_path, glob="*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    documents = loader.load()
    enhanced = []
    for doc in documents:
        filename = os.path.basename(doc.metadata.get('source', ''))
        route = ROUTE_MAPPING.get(filename, '')
        doc.metadata['route'] = route
        doc.metadata['type'] = 'content_markdown'
        enhanced.append(doc)
    if not enhanced:
        return None
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#","header1"),("##","header2"),("###","header3"),("####","header4")])
    text_splitter = MarkdownTextSplitter(chunk_size=1500, chunk_overlap=50)
    chunks = []
    for doc in enhanced:
        try:
            header_splits = header_splitter.split_text(doc.page_content)
            for split in header_splits:
                for chunk_text in text_splitter.split_text(split.page_content):
                    combined_metadata = {**doc.metadata, **split.metadata}
                    chunks.append(Document(page_content=chunk_text, metadata=combined_metadata))
        except Exception as e:
            logger.error(f"Error processing {doc.metadata.get('source','unknown')}: {e}")
            continue
    try:
        embedding = OpenAIEmbeddings(api_key=openai_api_key)
        _vector_db_cache = Chroma.from_documents(chunks, embedding)
        return _vector_db_cache
    except Exception as e:
        logger.error(f"Failed to create vector database: {e}")
        return None

def build_personalized_prompt(context: str, query: str, available_products=None, account_data: str = "", customer_info=None):
    available_products = available_products or []
    routes = get_all_route_mappings()
    route_context = "AVAILABLE NAVIGATION ROUTES:\n" + "\n".join([f"- {r} : {d}" for r,d in routes.items()]) + "\n\n"
    route_context += "NAVIGATION RULES:\n- Use simple markdown links: [visit reMIDI 4](/products/remidi-4)\n- Guide users to relevant products and pages\n- Focus on helping users find and buy products\n"
    customer_name = ""
    if customer_info:
        first = (customer_info.get('first_name') or '').strip()
        if first and first != 'N/A':
            customer_name = first
    if customer_name:
        greeting = f"""PERSONALIZATION:
- The customer's name is {customer_name}
- Use their first name in greetings: "Hi {customer_name}!"
- Be warm and personal
"""
    else:
        greeting = """PERSONALIZATION:
- Customer not logged in or no name
- Use friendly generic greetings
"""
    system_identity = f"""You are the SongWish AI Shopping Assistant. Help users find and buy music production products.

{greeting}

CORE MISSION:
- Help users discover the right products for their needs
- Guide them to product pages
- Provide simple, helpful navigation
- Be personal and friendly
"""
    products_for_prompt = ""
    if available_products:
        products_for_prompt = "AVAILABLE PRODUCTS TO RECOMMEND:\n" + "\n".join([f"- {p.get('display','Unknown')} [{p.get('attributes',{}).get('category','Other')}]: {p.get('description',{}).get('summary','No description')} - {p.get('total','N/A')}{' (ON SALE: '+p.get('discountPercent')+')' if p.get('discount') and p.get('discountPercent') else ''}" for p in available_products]) + "\n\nONLY recommend products from this list.\n"
    template = f"""{system_identity}

{route_context}

{products_for_prompt}

KNOWLEDGE BASE CONTEXT:
{context}

{"CUSTOMER ACCOUNT DATA:" if account_data else ""}
{account_data}

CUSTOMER QUERY: {query}
"""
    return template.strip()

def extract_cited_sources(response_text: str, source_names: list) -> list:
    import re
    cited_patterns = re.findall(r'\[Source (\d+)\]', response_text)
    cited_indices = sorted(set(int(i)-1 for i in cited_patterns if i.isdigit()))
    return [source_names[i] for i in cited_indices if 0 <= i < len(source_names)]
