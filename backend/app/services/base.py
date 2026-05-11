"""服务基类"""


class BaseService:
    """服务基类"""
    
    @staticmethod
    def success(data=None, message='成功'):
        """返回成功响应"""
        return {
            'code': 0,
            'message': message,
            'data': data
        }
    
    @staticmethod
    def error(code, message):
        """返回错误响应"""
        return {
            'code': code,
            'message': message,
            'data': None
        }
