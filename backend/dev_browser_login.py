"""开发用：调用登录 API 并在浏览器中写入 session（一次性页面）。"""
import json
import pathlib
import time
import urllib.request
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOTSTRAP = ROOT / 'frontend' / 'public' / '_dev_login.html'

USERNAME = 'student001'
PASSWORD = 'student123'


def main() -> None:
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/v1/auth/login',
        data=json.dumps({'username': USERNAME, 'password': PASSWORD}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    if resp.get('code') != 0:
        raise SystemExit(f"登录失败: {resp.get('message')}")

    payload = resp['data']
    profile = {
        k: v
        for k, v in payload.items()
        if k not in ('access_token', 'refresh_token', 'expiresIn')
    }
    profile_json = json.dumps(profile, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>登录中</title></head>
<body>
<p>正在以 {USERNAME} 登录…</p>
<script>
localStorage.setItem('a3_access_token', {json.dumps(payload['access_token'])});
localStorage.setItem('a3_refresh_token', {json.dumps(payload['refresh_token'])});
localStorage.setItem('a3_user_profile', {json.dumps(profile_json)});
window.location.replace('/student');
</script>
</body>
</html>"""

    BOOTSTRAP.write_text(html, encoding='utf-8')
    webbrowser.open('http://localhost:5173/_dev_login.html')
    print(f'已打开浏览器，账号 {USERNAME} 将跳转到 /student')
    time.sleep(3)
    try:
        BOOTSTRAP.unlink(missing_ok=True)
    except OSError:
        pass


if __name__ == '__main__':
    main()
