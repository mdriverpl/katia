"""WhatsApp Cloud API transport. Credentials never leave the backend."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class WhatsAppError(ValueError):
    pass


def public_url_issues():
    if not os.getenv("PUBLIC_APP_URL"):
        return []
    try:
        url = urlsplit(os.environ["PUBLIC_APP_URL"])
        if url.scheme == "https" and url.hostname and url.hostname not in ("localhost", "127.0.0.1", "::1") and not (url.username or url.password or url.query or url.fragment):
            return []
    except ValueError:
        pass
    return ["PUBLIC_APP_URL: podaj publiczny adres HTTPS aplikacji, bez parametrów i #."]


def configuration():
    names = ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_API_VERSION",
             "WHATSAPP_LINK_TEMPLATE", "WHATSAPP_REMINDER_TEMPLATE", "PUBLIC_APP_URL")
    missing = [name for name in names if not os.getenv(name, "").strip()]
    issues = public_url_issues()
    if os.getenv("WHATSAPP_API_VERSION") and not re.fullmatch(r"v\d+\.0", os.environ["WHATSAPP_API_VERSION"]):
        issues.append("WHATSAPP_API_VERSION: wpisz wersję API w formacie vNN.0.")
    if os.getenv("WHATSAPP_PHONE_NUMBER_ID") and not os.environ["WHATSAPP_PHONE_NUMBER_ID"].isdigit():
        issues.append("WHATSAPP_PHONE_NUMBER_ID: wymagany jest identyfikator liczbowy Meta.")
    return {"ready": not missing and not issues, "missing": missing, "issues": issues,
            "language": os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pl"),
            "link_template": os.getenv("WHATSAPP_LINK_TEMPLATE", ""),
            "reminder_template": os.getenv("WHATSAPP_REMINDER_TEMPLATE", "")}


def normalize_phone(value):
    phone = re.sub(r"[\s().-]", "", value or "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise WhatsAppError("W karcie klienta wpisz telefon z numerem kierunkowym kraju, np. +48123456789.")
    return phone[1:]


def send_template(phone, kind, parameters):
    if not configuration()["ready"]:
        raise WhatsAppError("Uzupełnij konfigurację WhatsApp w backend/.env i uruchom ponownie API.")
    number = normalize_phone(phone)
    template = os.environ["WHATSAPP_LINK_TEMPLATE" if kind == "link" else "WHATSAPP_REMINDER_TEMPLATE"]
    payload = {"messaging_product": "whatsapp", "to": number, "type": "template",
               "template": {"name": template, "language": {"code": os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pl")},
                            "components": [{"type": "body", "parameters": [{"type": "text", "text": str(value)} for value in parameters]}]}}
    request = Request(f'https://graph.facebook.com/{os.environ["WHATSAPP_API_VERSION"]}/{os.environ["WHATSAPP_PHONE_NUMBER_ID"]}/messages',
                      data=json.dumps(payload).encode(), method="POST",
                      headers={"Authorization": "Bearer " + os.environ["WHATSAPP_ACCESS_TOKEN"], "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        message_id = result["messages"][0]["id"]
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("Missing message ID")
        return message_id
    except HTTPError as exc:
        # Never expose provider response bodies, tokens or recipient information.
        raise WhatsAppError("Meta odrzuciła wiadomość. Sprawdź dostęp do API, numer odbiorcy i zatwierdzenie szablonu. Wysyłka nie została ponowiona.") from exc
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise WhatsAppError("Nie udało się potwierdzić wysyłki. Sprawdź wiadomość w Meta przed ponowieniem, aby uniknąć duplikatu.") from exc
