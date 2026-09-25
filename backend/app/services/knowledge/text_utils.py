# -*- coding: utf-8 -*-
"""中英混排文本的轻量分词、哈希与规范化工具（无第三方依赖）。"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter

_ASCII_TOKEN = re.compile(r'[A-Za-z_][A-Za-z0-9_\.]*|\d+(?:\.\d+)?')
_CJK = re.compile(r'[\u4e00-\u9fff]+')
_WHITESPACE = re.compile(r'\s+')

_STOPWORDS = {
    '的', '了', '是', '我', '在', '和', '吗', '呢', '啊', '这个', '那个', '什么', '怎么', '如何', '一下', '一个',
    '请问', '为什么', '可以', '应该', '会', '有', '就', '也', '都', '还', '把', '被', '与', '及', '或', '等',
    'the', 'a', 'an', 'is', 'are', 'to', 'of', 'in', 'and', 'or', 'for', 'on', 'with', 'how', 'what', 'why',
    'python',
}

# 中文问句填充语：在生成二元组之前从连续汉字串中剔除，避免“么意/是什”这类无信息二元组稀释覆盖率
_FILLER_PHRASES = (
    '是什么意思', '什么意思', '是什么', '什么是', '为什么', '怎么办', '怎么样', '能不能', '有没有',
    '请问', '帮我', '看看', '这个', '那个', '到底', '为何', '可以', '应该', '哪里', '哪个', '什么', '怎么',
    '如何', '怎样', '一下', '意思', '讲讲', '介绍', '解释', '一个',
    '吗', '呢', '啊', '的', '了', '是', '我', '在', '和', '把', '被', '与', '及', '或', '就', '也', '都', '还', '有', '会',
)
_FILLER_RE = re.compile('|'.join(sorted((re.escape(p) for p in _FILLER_PHRASES), key=len, reverse=True)))

_FULLWIDTH_MAP = str.maketrans({
    '，': ',', '。': '.', '？': '?', '！': '!', '：': ':', '；': ';', '（': '(', '）': ')', '【': '[', '】': ']',
    '“': '"', '”': '"', '‘': "'", '’': "'",
})


def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text or '')
    text = text.translate(_FULLWIDTH_MAP)
    return _WHITESPACE.sub(' ', text).strip()


def tokenize(text: str, *, bigrams: bool = True, drop_stopwords: bool = True) -> list[str]:
    """中文按字 + 相邻字二元组，英文/标识符按词；统一小写。"""
    text = normalize_text(text).lower()
    tokens: list[str] = []
    for match in _ASCII_TOKEN.finditer(text):
        token = match.group(0).strip('.')
        if token and (not drop_stopwords or token not in _STOPWORDS):
            tokens.append(token)
    for match in _CJK.finditer(text):
        runs = [match.group(0)]
        if drop_stopwords:
            runs = [r for r in _FILLER_RE.split(match.group(0)) if r]
        for run in runs:
            chars = list(run)
            tokens.extend(chars)
            if bigrams:
                tokens.extend(a + b for a, b in zip(chars, chars[1:]))
    if drop_stopwords:
        tokens = [t for t in tokens if t not in _STOPWORDS]
    return tokens


def term_counts(text: str) -> Counter:
    return Counter(tokenize(text))


def content_hash(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def stable_hash(text: str, length: int = 16) -> str:
    return hashlib.sha1((text or '').encode('utf-8')).hexdigest()[:length]


def estimate_tokens(text: str) -> int:
    """粗略 token 估算：中文按字、英文按 ~4 字符。"""
    if not text:
        return 0
    cjk = len(_CJK.findall(text)) and sum(len(m) for m in _CJK.findall(text))
    ascii_len = len(text) - cjk
    return int(cjk + ascii_len / 4)


def truncate(text: str, limit: int) -> str:
    text = text or ''
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + '…'


def redact_preview(text: str, limit: int) -> str:
    """日志用预览：截断并去掉疑似邮箱/手机号/长数字串。"""
    text = normalize_text(text)
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[email]', text)
    text = re.sub(r'\b1\d{10}\b', '[phone]', text)
    text = re.sub(r'\b\d{8,}\b', '[number]', text)
    return truncate(text, limit)
