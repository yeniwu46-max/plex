"""Interactive local configuration. Never echoes the QQ authorization code."""
from getpass import getpass
from pathlib import Path
import re
import smtplib
import ssl
from dotenv import set_key


def main():
    email = input('QQ email address: ').strip().lower()
    if not re.fullmatch(r'[^\s@]+@(qq\.com|foxmail\.com)', email):
        raise SystemExit('Please enter your QQ/Foxmail email address.')
    password = getpass('QQ SMTP authorization code (hidden; not your QQ password): ').strip()
    if not password:
        raise SystemExit('No code entered; configuration unchanged.')
    try:
        with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=15, context=ssl.create_default_context()) as smtp:
            smtp.login(email, password)
    except Exception:
        raise SystemExit('SMTP login failed. Check SMTP is enabled and the authorization code is correct; no file changed.')
    target = Path(__file__).resolve().parents[1] / '.env.smtp.local'
    for key, value in {'SMTP_HOST':'smtp.qq.com','SMTP_PORT':'465','SMTP_USER':email,'SMTP_PASSWORD':password,'AUTH_SUPPORT_EMAIL':email}.items():
        set_key(str(target), key, value)
    print('SMTP login verified. Saved to backend/.env.smtp.local (Git ignored). Restart the backend to enable recovery. No email sent.')


if __name__ == '__main__':
    main()
