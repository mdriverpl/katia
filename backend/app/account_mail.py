"""SMTP delivery of initial account credentials; secrets never enter API responses."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_welcome(email: str, password: str, config=None):
    config = config or {}
    def setting(name, default=""):
        return config.get(name, os.getenv(name, default))
    host = setting("SMTP_HOST")
    sender = setting("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("SMTP is not configured")
    mode = setting("SMTP_SECURITY", "starttls")
    if mode not in {"starttls", "ssl"}:
        raise RuntimeError("SMTP requires TLS")
    port = int(setting("SMTP_PORT", "465" if mode == "ssl" else "587"))
    message = EmailMessage()
    message["Subject"] = "Space & Flow — Twoje konto"
    message["From"] = sender
    message["To"] = email
    url = setting("PUBLIC_APP_URL").strip()
    message.set_content(
        f"Utworzono Twoje konto w Space & Flow.\n\nLogin: {email}\n"
        f"Hasło tymczasowe: {password}\n\n"
        + (f"Panel: {url}\n\n" if url else "")
        + "Przy pierwszym logowaniu ustaw własne hasło.\n"
    )
    context = ssl.create_default_context()
    connection = smtplib.SMTP_SSL(host, port, timeout=20, context=context) if mode == "ssl" else smtplib.SMTP(host, port, timeout=20)
    with connection as smtp:
        if mode == "starttls":
            smtp.starttls(context=context)
        username = setting("SMTP_USERNAME")
        if username:
            smtp.login(username, setting("SMTP_PASSWORD"))
        if smtp.send_message(message):
            raise RuntimeError("Recipient rejected")
