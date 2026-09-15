import secrets
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _split_csv(value: str) -> list[str]: return [x.strip() for x in value.split(',') if x.strip()]

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True, extra='ignore')
    PROJECT_NAME: str='Nexa - AI Educational Marketplace'
    API_V1_STR: str='/api/v1'
    ENVIRONMENT: str='development'
    SECRET_KEY: str=''
    ALGORITHM: str='HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES:int=60
    REFRESH_TOKEN_EXPIRE_DAYS:int=30
    DATABASE_URL:str='sqlite+aiosqlite:///./ai_edu.db'
    TEACHER_SHARE_PCT:float=.80
    PLATFORM_SHARE_PCT:float=.20
    # Local-only AI: Ollama runs on this PC. No cloud API key is required.
    LOCAL_LLM_BASE_URL:str='http://127.0.0.1:11434'
    LOCAL_LLM_MODEL:str='qwen2.5:7b'
    SENTRY_DSN:str=''
    ALLOWED_HOSTS:str='localhost,127.0.0.1'
    CORS_ORIGINS:str='http://localhost:8000,http://127.0.0.1:8000'
    RATE_LIMIT_PER_MINUTE:int=120
    LOGIN_RATE_LIMIT_PER_MINUTE:int=10
    UPLOAD_MAX_MB:int=500
    TEACHER_STORAGE_QUOTA_GB:int=100
    STUDENT_STORAGE_QUOTA_GB:int=5
    STORAGE_PATH:str='static/uploads'
    STORAGE_BACKEND:str='local'
    S3_ENDPOINT_URL:str=''
    S3_ACCESS_KEY_ID:str=''
    S3_SECRET_ACCESS_KEY:str=''
    S3_BUCKET:str=''
    S3_REGION:str='auto'
    PRESIGNED_URL_TTL:int=900
    REDIS_URL:str=''
    ENABLE_SCHEDULER:bool=False
    ENABLE_WORKER:bool=False
    SMTP_HOST:str=''
    SMTP_PORT:int=587
    SMTP_USERNAME:str=''
    SMTP_PASSWORD:str=''
    SMTP_FROM_EMAIL:str=''
    SMTP_USE_TLS:bool=True
    FRONTEND_BASE_URL:str='http://localhost:8000'
    PASSWORD_RESET_TTL_MINUTES:int=30
    EMAIL_VERIFICATION_TTL_HOURS:int=24
    PAYMOB_SECRET_KEY:str=''
    PAYMOB_PUBLIC_KEY:str=''
    PAYMOB_INTEGRATION_ID:str=''
    PAYMOB_IFRAME_ID:str=''
    PAYMOB_WEBHOOK_HMAC_SECRET:str=''
    PAYMOB_BASE_URL:str='https://accept.paymob.com'
    PAYMENT_CURRENCY:str='EGP'
    LIVEKIT_URL:str=''
    LIVEKIT_API_KEY:str=''
    LIVEKIT_API_SECRET:str=''
    CLAMAV_HOST:str=''
    CLAMAV_PORT:int=3310
    REQUIRE_ANTIVIRUS:bool=False
    FFMPEG_BINARY:str='ffmpeg'
    FFPROBE_BINARY:str='ffprobe'
    VECTOR_TOP_K:int=5
    ADMIN_EMAIL:str='admin@platform.com'
    ADMIN_PASSWORD:str='Admin@123456'
    ADMIN_FULL_NAME:str='المدير العام للمنصة'
    @computed_field
    @property
    def allowed_hosts_list(self)->list[str]: return _split_csv(self.ALLOWED_HOSTS)
    @computed_field
    @property
    def cors_origins_list(self)->list[str]: return _split_csv(self.CORS_ORIGINS)

settings=Settings()

def validate_production_settings():
    if settings.ENVIRONMENT.lower() not in {'production','prod'}: return
    if not settings.SECRET_KEY or len(settings.SECRET_KEY)<32: raise RuntimeError('Production requires SECRET_KEY >= 32 chars.')
    if not settings.ADMIN_PASSWORD or len(settings.ADMIN_PASSWORD)<12: raise RuntimeError('Production requires ADMIN_PASSWORD.')
    if not settings.DATABASE_URL.lower().startswith('postgresql+asyncpg://'): raise RuntimeError('Production requires PostgreSQL via postgresql+asyncpg://')
    if not settings.REDIS_URL: raise RuntimeError('Production requires REDIS_URL.')
    if settings.STORAGE_BACKEND != 's3': raise RuntimeError('Production requires STORAGE_BACKEND=s3 with private bucket.')
    if not settings.S3_ENDPOINT_URL or not settings.S3_BUCKET or not settings.S3_ACCESS_KEY_ID or not settings.S3_SECRET_ACCESS_KEY: raise RuntimeError('Production requires S3/R2 credentials.')
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL: raise RuntimeError('Production requires SMTP configuration.')
    if not settings.PAYMOB_SECRET_KEY or not settings.PAYMOB_WEBHOOK_HMAC_SECRET: raise RuntimeError('Production requires Paymob credentials/webhook secret.')
    if any(x in settings.CORS_ORIGINS.lower() for x in ('localhost','127.0.0.1')): raise RuntimeError('Production CORS cannot contain localhost.')
    if any(x in settings.ALLOWED_HOSTS.lower() for x in ('localhost','127.0.0.1')): raise RuntimeError('Production ALLOWED_HOSTS cannot contain localhost.')
