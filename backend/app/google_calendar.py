"""Google OAuth and one-way calendar export. No application secrets are logged."""
import base64
import hashlib
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SCOPE = "https://www.googleapis.com/auth/calendar.app.created"
API = "https://www.googleapis.com/calendar/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CALLBACK_PATH = "/api/integrations/google-calendar/callback"


class GoogleError(Exception):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


def request(method, url, data=None, token=None, form=False):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = (urlencode(data) if form else json.dumps(data)).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        status = error.code
        error.close()
        message = "Google odrzucił żądanie. Sprawdź konfigurację i dostęp do kalendarza."
        if status in (400, 401):
            message = "Google odrzucił autoryzację. Sprawdź ustawienia OAuth lub ponownie połącz konto."
        elif status == 403:
            message = "Brak uprawnień Google. Sprawdź włączenie Calendar API i zgodę na dostęp."
        elif status == 429:
            message = "Limit zapytań Google. Spróbuj ponownie później."
        raise GoogleError(message, status) from None
    except (URLError, OSError, ValueError):
        raise GoogleError("Nie udało się połączyć z Google. Spróbuj ponownie później.") from None


def authorization_url(client_id, redirect_uri, state, verifier):
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })


def exchange_code(client_id, client_secret, redirect_uri, code, verifier):
    result = request("POST", TOKEN_URL, {"client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri, "code": code, "code_verifier": verifier,
        "grant_type": "authorization_code"}, form=True)
    if not result.get("refresh_token") or not result.get("access_token") or SCOPE not in result.get("scope", "").split():
        raise GoogleError("Google nie udzielił trwałego dostępu do kalendarza. Ponownie połącz konto i zaakceptuj uprawnienia.")
    return result


def refresh_access(client_id, client_secret, refresh_token):
    result = request("POST", TOKEN_URL, {"client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token"}, form=True)
    if not result.get("access_token"):
        raise GoogleError("Brak tokena dostępu Google. Ponownie połącz konto.")
    return result["access_token"]


def create_calendar(token):
    result = request("POST", API + "/calendars", {"summary": "Space & Flow", "timeZone": "Europe/Warsaw",
        "description": "Terminy z aplikacji Space & Flow. Zmieniaj je w aplikacji; eksport jest jednokierunkowy."}, token)
    if not result.get("id"):
        raise GoogleError("Google nie zwrócił identyfikatora kalendarza.")
    return result["id"]


def event_body(event, client_name, namespace):
    due = event["due_date"]
    if isinstance(due, str):
        due = date.fromisoformat(due)
    hour = (event.get("scheduled_time") or "").strip()
    description = ["Termin z aplikacji Space & Flow.", f"Status: {event.get('status') or 'planowany'}"]
    if client_name:
        description.append(f"Klient: {client_name}")
    # Free-form times cannot be safely interpreted; retain them in the description.
    if re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", hour):
        h, m = map(int, hour.split(":"))
        start = datetime(due.year, due.month, due.day, h, m, tzinfo=ZoneInfo("Europe/Warsaw"))
        end = (start.astimezone(timezone.utc) + timedelta(hours=1)).astimezone(ZoneInfo("Europe/Warsaw"))
        period = {"start": {"dateTime": start.isoformat(), "timeZone": "Europe/Warsaw"},
                  "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Warsaw"}}
    else:
        period = {"start": {"date": due.isoformat()}, "end": {"date": (due + timedelta(days=1)).isoformat()}}
        if hour:
            description.append(f"Godzina: {hour}")
    return {"summary": event["title"], "description": "\n".join(description), "location": event.get("address") or "",
            "status": "confirmed", **period,
            "extendedProperties": {"private": {"space_flow": namespace, "source_id": str(event["id"])}}}


def same_event(remote, desired):
    for key in ("summary", "description", "location", "status"):
        if remote.get(key, "") != desired[key]:
            return False
    for key in ("start", "end"):
        actual, expected = remote.get(key, {}), desired[key]
        if "date" in expected:
            if actual.get("date") != expected["date"]:
                return False
        else:
            try:
                if datetime.fromisoformat(actual["dateTime"]) != datetime.fromisoformat(expected["dateTime"]):
                    return False
            except (KeyError, ValueError):
                return False
    return True


def sync_events(token, calendar_id, namespace, events, client_names):
    """Reconcile only this installation's events, including interrupted prior exports."""
    base = API + "/calendars/" + quote(calendar_id, safe="") + "/events"
    remote = {}
    page = None
    while True:
        params = {"privateExtendedProperty": "space_flow=" + namespace, "maxResults": 2500}
        if page:
            params["pageToken"] = page
        result = request("GET", base + "?" + urlencode(params), token=token)
        for item in result.get("items", []):
            if item.get("status") != "cancelled":
                remote[item["id"]] = item
        page = result.get("nextPageToken")
        if not page:
            break
    desired = {str(item["id"]): event_body(item, client_names.get(item.get("company_id"), ""), namespace)
               for item in events if item.get("due_date")}
    by_source = {}
    for remote_id, item in remote.items():
        source = item.get("extendedProperties", {}).get("private", {}).get("source_id")
        by_source.setdefault(source, []).append(remote_id)
    counts = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}
    started = time.monotonic()
    keep = set()
    for source, body in desired.items():
        if time.monotonic() - started > 120:
            raise GoogleError("Część terminów została wysłana. Ponów synchronizację, aby dokończyć eksport.")
        existing_ids = by_source.get(source, [])
        if existing_ids:
            remote_id = existing_ids[0]
            if same_event(remote[remote_id], body):
                counts["unchanged"] += 1
            else:
                request("PUT", base + "/" + quote(remote_id, safe=""), body, token)
                counts["updated"] += 1
        else:
            # Stable IDs make an insert safe to repeat after network/DB failures.
            remote_id = hashlib.sha256((namespace + ":" + source).encode()).hexdigest()
            for attempt in range(10):
                try:
                    request("POST", base, {"id": remote_id, **body}, token)
                    counts["created"] += 1
                    break
                except GoogleError as error:
                    if error.status != 409:
                        raise
                    try:
                        previous = request("GET", base + "/" + remote_id, token=token)
                    except GoogleError as gone:
                        if gone.status != 410:
                            raise
                        previous = {"status": "cancelled"}
                    if previous.get("status") != "cancelled":
                        properties = previous.get("extendedProperties", {}).get("private", {})
                        if properties != body["extendedProperties"]["private"]:
                            raise GoogleError("Konflikt identyfikatora wydarzenia Google.")
                        request("PUT", base + "/" + remote_id, body, token)
                        counts["updated"] += 1
                        break
                    remote_id = hashlib.sha256((remote_id + ":restore").encode()).hexdigest()
            else:
                raise GoogleError("Nie udało się odtworzyć usuniętego wydarzenia Google.")
        keep.add(remote_id)
    for remote_id in remote.keys() - keep:
        try:
            request("DELETE", base + "/" + quote(remote_id, safe=""), token=token)
        except GoogleError as error:
            if error.status not in (404, 410):
                raise
        counts["deleted"] += 1
    return counts
