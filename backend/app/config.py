import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    基础配置类 - 所有环境共享的配置
    """
    # ============ Flask 基础配置 ============
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # ============ 数据库配置 ============
    # MySQL 连接字符串格式: mysql+pymysql://user:password@host:port/database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:password@localhost:3306/learning_system'
    )

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


class DevelopmentConfig(Config):
    """
    开发环境配置
    特点: 调试模式开启，详细日志输出
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True  # 打印SQL语句
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """
    测试环境配置
    特点: 使用内存SQLite数据库，快速测试
    """
    TESTING = True
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

    if not SECRET_KEY:
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
    if not JWT_SECRET_KEY:
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

    return config.get(env, config['default'])
