import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    T_STATUS = os.environ.get("DDB_TABLE_STATUS", "virtual-dealer-status-checks")
    T_LEADS = os.environ.get("DDB_TABLE_LEADS", "virtual-dealer-leads")
    T_CHAT = os.environ.get("DDB_TABLE_CHAT", "virtual-dealer-chat-logs")
    
    LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY')
    LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_BASE_URL = os.environ.get('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')
    
    CHAT_LOG_TTL_DAYS = int(os.environ.get("CHAT_LOG_TTL_DAYS", "30"))
    
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    MODEL_ENDPOINT = os.environ.get('MODEL_ENDPOINT')
    MODEL_ID = os.environ.get('MODEL_ID', 'claude-sonnet-4.6')
    EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
    
    LLM_PROXY_SECRET = os.environ.get('LLM_PROXY_SECRET', '')
    
    AGORA_APP_ID = os.environ.get('AGORA_APP_ID')
    AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE')
    AGORA_CUSTOMER_ID = os.environ.get('AGORA_CUSTOMER_ID')
    AGORA_CUSTOMER_SECRET = os.environ.get('AGORA_CUSTOMER_SECRET')
    
    PUBLIC_BACKEND_URL = os.environ.get('PUBLIC_BACKEND_URL')
    REACT_APP_BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

settings = Settings()
