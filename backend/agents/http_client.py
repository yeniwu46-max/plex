"""HTTP client for external LLM/API calls.

本机若通过系统代理（Clash 等）才能访问外部大模型 API，`trust_env=False`
的纯直连会超时（初赛讯飞冒烟 network_error 的根因）。代理解析顺序：

1. ``LLM_HTTP_PROXY`` 环境变量（设为 ``off``/``none``/``direct`` 可强制直连）；
2. Windows 系统代理（WinINET 注册表）；
3. 都没有则直连。

localhost / 127.0.0.1 请求始终直连，避免代理劫持本地调用。
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

try:
    # 代理若做 TLS 中间人（证书装在 Windows 证书库），certifi 会报 SSLError；
    # truststore 让 Python 复用操作系统证书库。必须在创建 Session 之前注入。
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import requests

_DIRECT = requests.Session()
_DIRECT.trust_env = False


def _windows_system_proxy() -> str | None:
    if os.name != 'nt':
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
        ) as key:
            enabled, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            server, _ = winreg.QueryValueEx(key, 'ProxyServer')
    except OSError:
        return None
    if not enabled or not server:
        return None
    server = str(server).strip()
    if '=' in server:
        # 形如 http=127.0.0.1:7897;https=127.0.0.1:7897 的协议级配置
        for part in server.split(';'):
            part = part.strip()
            if part.startswith('https='):
                return f'http://{part[6:]}'
            if part.startswith('http='):
                return f'http://{part[5:]}'
        return None
    return f'http://{server}'


def _resolve_proxy() -> str | None:
    configured = os.getenv('LLM_HTTP_PROXY', '').strip()
    if configured.lower() in {'off', 'none', 'direct'}:
        return None
    if configured:
        return configured
    return _windows_system_proxy()


_PROXY = _resolve_proxy()
_LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}


def _with_proxy(url: str, kwargs: dict) -> dict:
    if _PROXY and 'proxies' not in kwargs:
        host = urlparse(url).hostname
        if host not in _LOCAL_HOSTS:
            kwargs['proxies'] = {'http': _PROXY, 'https': _PROXY}
    return kwargs


def _request_with_retry(method: str, url: str, *args, **kwargs):
    """本机代理/TUN 冷启动时首个请求常超时、重试即成功，故默认重试 1 次。

    重试发生在收到任何响应字节之前（连接失败/超时），对上游是安全的。
    """
    retries = max(0, int(os.getenv('LLM_HTTP_RETRIES', '1')))
    host = urlparse(url).hostname
    if host in _LOCAL_HOSTS:
        retries = 0
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            return getattr(_DIRECT, method)(url, *args, **_with_proxy(url, dict(kwargs)))
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
    raise last_error


def direct_post(url, *args, **kwargs):
    return _request_with_retry('post', url, *args, **kwargs)


def direct_get(url, *args, **kwargs):
    return _request_with_retry('get', url, *args, **kwargs)
