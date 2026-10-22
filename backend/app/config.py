import os
from datetime import timedelta
from dotenv import load_dotenv

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv()
# Local provider overrides are ignored by git and intentionally take precedence
# over the shared development .env file.
load_dotenv(os.path.join(BACKEND_ROOT, '.env.spark.local'), override=True)
load_dotenv(os.path.join(BACKEND_ROOT, '.env.smtp.local'), override=True)
load_dotenv(os.path.join(BACKEND_ROOT, '.env.execution.local'), override=True)
load_dotenv(os.path.join(BACKEND_ROOT, '.env.learning.local'), override=True)
INSTANCE_DIR = os.path.join(BACKEND_ROOT, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)
DEFAULT_SQLITE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'learning_system.db').replace('\\', '/')


def _resolve_database_uri(raw: str | None) -> str:
    uri = raw or DEFAULT_SQLITE_URI
    if not uri.startswith('sqlite:///') or uri.startswith('sqlite:////'):
        return uri
    relative = uri[len('sqlite:///'):]
    if relative in (':memory:', '') or os.path.isabs(relative):
        return uri
    absolute = os.path.join(BACKEND_ROOT, relative).replace('\\', '/')
    return f'sqlite:///{absolute}'


class Config:
    LEARNER_STATE_READ_MODE = os.getenv('LEARNER_STATE_READ_MODE', 'shadow')
    COUNTEREXAMPLE_GENERATION_WORKER_ENABLED = os.getenv('COUNTEREXAMPLE_GENERATION_WORKER_ENABLED', 'true').lower() == 'true'
    COUNTEREXAMPLE_GENERATION_ACTIVE_LIMIT = int(os.getenv('COUNTEREXAMPLE_GENERATION_ACTIVE_LIMIT', '2'))
    COUNTEREXAMPLE_GENERATION_DAILY_LIMIT = int(os.getenv('COUNTEREXAMPLE_GENERATION_DAILY_LIMIT', '10'))
    COUNTEREXAMPLE_CLASS_DAILY_LIMIT = int(os.getenv('COUNTEREXAMPLE_CLASS_DAILY_LIMIT','20'))
    COUNTEREXAMPLE_CLASS_ACTIVE_LIMIT = int(os.getenv('COUNTEREXAMPLE_CLASS_ACTIVE_LIMIT','4'))
    COUNTEREXAMPLE_GLOBAL_ACTIVE_LIMIT = int(os.getenv('COUNTEREXAMPLE_GLOBAL_ACTIVE_LIMIT','8'))
    LEARNER_STATE_WORKER_ENABLED = os.getenv('LEARNER_STATE_WORKER_ENABLED', 'true').lower() == 'true'
    """
    基础配置类 - 所有环境共享的配置
    """
    # ============ Flask 基础配置 ============
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    STORE_MOCK_ACTIVATION_ENABLED = False
    TUTOR_DAILY_REQUEST_LIMIT = int(os.getenv('TUTOR_DAILY_REQUEST_LIMIT', '80'))
    TUTOR_USER_CONCURRENCY = int(os.getenv('TUTOR_USER_CONCURRENCY', '2'))
    TUTOR_GLOBAL_CONCURRENCY = int(os.getenv('TUTOR_GLOBAL_CONCURRENCY', '8'))
    TUTOR_REQUEST_ATTEMPT_LIMIT = int(os.getenv('TUTOR_REQUEST_ATTEMPT_LIMIT', '3'))
    AI_MODEL_RATE_CARD_FILE = os.getenv('AI_MODEL_RATE_CARD_FILE', '')
    RAG_DAILY_REQUEST_LIMIT = int(os.getenv('RAG_DAILY_REQUEST_LIMIT', '40'))
    RAG_USER_CONCURRENCY = int(os.getenv('RAG_USER_CONCURRENCY', '2'))
    RAG_GLOBAL_CONCURRENCY = int(os.getenv('RAG_GLOBAL_CONCURRENCY', '8'))
    RAG_REQUEST_ATTEMPT_LIMIT = int(os.getenv('RAG_REQUEST_ATTEMPT_LIMIT', '3'))
    RESOURCE_USER_DAILY_LIMIT = int(os.getenv('RESOURCE_USER_DAILY_LIMIT','10'))
    RESOURCE_CLASS_DAILY_LIMIT = int(os.getenv('RESOURCE_CLASS_DAILY_LIMIT','60'))
    RESOURCE_USER_ACTIVE_LIMIT = int(os.getenv('RESOURCE_USER_ACTIVE_LIMIT','2'))
    RESOURCE_CLASS_ACTIVE_LIMIT = int(os.getenv('RESOURCE_CLASS_ACTIVE_LIMIT','6'))
    RESOURCE_GLOBAL_ACTIVE_LIMIT = int(os.getenv('RESOURCE_GLOBAL_ACTIVE_LIMIT','12'))
    RESOURCE_ATTEMPTS_LIMIT = int(os.getenv('RESOURCE_ATTEMPTS_LIMIT','3'))
    CODE_EXECUTION_BACKEND = os.getenv('CODE_EXECUTION_BACKEND', 'auto')
    # Open only after the isolated trace acceptance script has passed.
    CODE_TRACE_ENABLED = os.getenv('CODE_TRACE_ENABLED', 'false').lower() in {'true', '1', 'yes'}
    CODE_EXECUTION_DOCKER_IMAGE = os.getenv('CODE_EXECUTION_DOCKER_IMAGE', 'plex-python-sandbox:1')
    JUDGE0_API_URL = os.getenv('JUDGE0_API_URL', '')
    JUDGE0_AUTH_TOKEN = os.getenv('JUDGE0_AUTH_TOKEN', '')

    # ============ 数据库配置 ============
    # MySQL 连接字符串格式: mysql+pymysql://user:password@host:port/database
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(os.getenv('DATABASE_URL'))

    # SQLAlchemy配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 不跟踪模型修改，节省内存
    SQLALCHEMY_ECHO = False  # 是否输出SQL语句
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,  # 连接池大小
        'pool_recycle': 3600,  # 回收连接时间（秒）
        'pool_pre_ping': True,  # 连接前检测
        'max_overflow': 20,  # 超出pool_size后的最大连接数
    }

    # ============ JWT 认证配置 ============
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # access token 24小时过期
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)   # refresh token 7天过期
    JWT_TOKEN_LOCATION = ['headers']  # Token位置：Headers
    JWT_HEADER_NAME = 'Authorization'  # Header名
    JWT_HEADER_TYPE = 'Bearer'  # Token类型前缀

    # ============ 应用配置 ============
    JSON_SORT_KEYS = False  # 不排序JSON键
    JSON_AS_ASCII = False  # 允许非ASCII字符（中文）

    # ============ 日志配置 ============
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
    AUTH_RATE_LIMIT_ENABLED = True
    AUTH_SUPPORT_EMAIL = os.getenv('AUTH_SUPPORT_EMAIL', '')
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

    # OAuth login configuration. Set these in the backend environment before
    # enabling the Google/GitHub buttons in production.
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5180')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')

    # Alipay merchant face-to-face QR payments. Live payments remain disabled
    # until all merchant credentials and a public HTTPS notify URL are present.
    ALIPAY_PAYMENT_ENABLED = os.getenv('ALIPAY_PAYMENT_ENABLED', 'false').lower() == 'true'
    ALIPAY_APP_ID = os.getenv('ALIPAY_APP_ID', '')
    ALIPAY_PRIVATE_KEY = os.getenv('ALIPAY_PRIVATE_KEY', '')
    ALIPAY_PUBLIC_KEY = os.getenv('ALIPAY_PUBLIC_KEY', '')
    ALIPAY_SELLER_ID = os.getenv('ALIPAY_SELLER_ID', '')
    ALIPAY_NOTIFY_URL = os.getenv('ALIPAY_NOTIFY_URL', '')
    ALIPAY_GATEWAY = os.getenv('ALIPAY_GATEWAY', 'https://openapi.alipay.com/gateway.do')
    ALIPAY_QR_TIMEOUT_MINUTES = int(os.getenv('ALIPAY_QR_TIMEOUT_MINUTES', '15'))


class DevelopmentConfig(Config):
    """
    开发环境配置
    特点: 调试模式开启，详细日志输出
    """
    DEBUG = True
    STORE_MOCK_ACTIVATION_ENABLED = True
    # SQL bind values may contain private teaching material; logging is opt-in.
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    LEARNER_STATE_READ_MODE = 'shadow'
    LEARNER_STATE_WORKER_ENABLED = False
    """
    测试环境配置
    特点: 使用内存SQLite数据库，快速测试
    """
    TESTING = True
    # Tests must inject deterministic runners or explicitly enable a real
    # isolated integration target; never use developer provider credentials.
    CODE_EXECUTION_BACKEND = 'disabled'
    JUDGE0_API_URL = ''
    JUDGE0_AUTH_TOKEN = ''
    AUTH_RATE_LIMIT_ENABLED = False
    STORE_MOCK_ACTIVATION_ENABLED = True
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 内存数据库
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """
    生产环境配置
    特点: 调试关闭，安全配置，性能优化
    """
    DEBUG = False
    TESTING = False

    # 确保生产环境必须配置环境变量
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')


def _validate_production_config(cfg: type[Config]) -> None:
    if cfg is not ProductionConfig:
        return
    if not cfg.SECRET_KEY:
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
    if not cfg.JWT_SECRET_KEY:
        raise ValueError("生产环境必须设置 JWT_SECRET_KEY 环境变量")


# 配置映射表
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    获取配置对象

    Args:
        env: 环境名 ('development', 'testing', 'production')
             如果不提供，从FLASK_ENV环境变量读取

    Returns:
        Config 类
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')

    cfg = config.get(env, config['default'])
    _validate_production_config(cfg)
    return cfg
