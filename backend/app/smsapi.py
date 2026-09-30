"""SMSAPI.pl transport; single recipient and no automatic HTTP retries."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .whatsapp import normalize_phone, WhatsAppError, public_url_issues


class SmsApiError(ValueError):
    pass


def configuration():
    missing = [name for name in ("SMSAPI_ACCESS_TOKEN", "SMSAPI_SENDER", "PUBLIC_APP_URL") if not os.getenv(name, "").strip()]
    issues = public_url_issues()
    return {"ready": not missing and not issues, "missing": missing, "issues": issues,
            "sender": os.getenv("SMSAPI_SENDER", "")}


def message_text(kind, parameters):
    if kind == "link":
        name, url = parameters
        return f"Dzień dobry {name}, Twój terminarz: {url} — Space & Flow"
    name, title, day, time, address = parameters
    return f"Dzień dobry {name}, przypominamy: {title}, {day}, godzina: {time}. Adres: {address}. Space & Flow"


def send_message(phone, kind, parameters):
    if not configuration()["ready"]:
        raise SmsApiError("Uzupełnij konfigurację SMSAPI w backend/.env i uruchom ponownie API.")
    try:
        number = normalize_phone(phone)
    except WhatsAppError as exc:
        raise SmsApiError(str(exc)) from exc
    payload = {"to": number, "from": os.environ["SMSAPI_SENDER"], "message": message_text(kind, parameters), "format": "json", "encoding": "utf-8"}
    request = Request("https://api.smsapi.pl/sms.do", data=urlencode(payload).encode(), method="POST",
                      headers={"Authorization": "Bearer " + os.environ["SMSAPI_ACCESS_TOKEN"], "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        if result.get("error") or result.get("invalid_numbers"):
            raise SmsApiError("SMSAPI odrzuciło SMS. Sprawdź saldo, token, nadawcę i numer odbiorcy w panelu SMSAPI.")
        item = result["list"][0]
        if item.get("error") or item.get("status") in ("ERROR", "FAILED", "REJECTED"):
            raise SmsApiError("SMSAPI odrzuciło SMS. Sprawdź szczegóły w panelu SMSAPI.")
        message_id = item["id"]
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("Missing SMS ID")
        return message_id
    except HTTPError as exc:
        raise SmsApiError("SMSAPI odrzuciło żądanie. Sprawdź token i konfigurację konta. Wysyłka nie została ponowiona.") from exc
    except SmsApiError:
        raise
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise SmsApiError("Nie udało się potwierdzić wysyłki SMS. Sprawdź panel SMSAPI przed ponowieniem, aby uniknąć duplikatu.") from exc
