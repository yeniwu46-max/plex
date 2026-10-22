"""Infrastructure failures are retryable, never a student's wrong answer."""


class ExecutionUnavailable(RuntimeError):
    def __init__(self, reason: str = 'unavailable'):
        self.reason = reason
        super().__init__('隔离执行环境暂不可用，请稍后重试；本次不计入作答结果。')


class ExecutionInputError(ValueError):
    pass
