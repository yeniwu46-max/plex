"""Shared safety checks for Python-course AI surfaces."""
from __future__ import annotations

import re


class SafetyViolation(ValueError):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message)
        self.reason_code = reason_code


class CourseSafetyService:
    INJECTION_PATTERNS = (
        r'忽略.{0,12}(之前|以上|系统|指令)',
        r'(显示|泄露|输出).{0,12}(系统提示|prompt|密钥|api key)',
        r'you are now',
        r'ignore (all|previous|above) instructions',
        r'ignore .{0,24} instructions',
        r'jailbreak',
        r'developer message',
    )
    SENSITIVE_PATTERNS = (
        r'色情|赌博|毒品|自杀|恐怖主义|制作炸弹',
        r'\bporn\b|\bterrorism\b',
        r'\bmake (a )?bomb\b|\billegal drugs?\b|\bsuicide instructions?\b',
    )
    OUT_OF_SCOPE_PATTERNS = (
        r'medical diagnosis|legal advice|stock recommendation|lottery prediction',
        r'write my (history|chemistry|english) essay',
        r'诊断疾病|开处方|法律意见|股票推荐|彩票预测',
        r'化学方程式|历史论文|英语作文代写',
    )

    @staticmethod
    def _matches(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    @classmethod
    def ensure_safe(cls, text: str, *, enforce_course_scope: bool = False) -> None:
        normalized = str(text or '').strip()
        if cls._matches(normalized, cls.INJECTION_PATTERNS):
            raise SafetyViolation('请求包含提示注入或系统信息窃取意图', 'prompt_injection')
        if cls._matches(normalized, cls.SENSITIVE_PATTERNS):
            raise SafetyViolation('请求包含不允许的敏感内容', 'sensitive_content')
        if enforce_course_scope and cls._matches(normalized, cls.OUT_OF_SCOPE_PATTERNS):
            raise SafetyViolation('请求超出 Python 课程学习范围', 'out_of_course_scope')
