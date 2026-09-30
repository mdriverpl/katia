"""Daily overview and optional AI wording based only on aggregate counts."""
import hashlib
import json
import os
import threading
import time
from datetime import timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CLOSED = {"wykonany", "zakończony", "zakończona", "gotowy", "wydany", "anulowany", "anulowana", "done", "completed", "cancelled", "canceled"}
_cache = {}
_lock = threading.Lock()


def build_overview(events, services, today):
    pending = [event for event in events if str(event.get("status", "")).strip().lower() not in CLOSED]
    todays = [event for event in pending if event.get("due_date") == today]
    overdue = [event for event in pending if event.get("due_date") and event["due_date"] < today]
    tomorrow = [event for event in pending if event.get("due_date") == today + timedelta(days=1)]
    stats = {"today": len(todays), "overdue": len(overdue), "tomorrow": len(tomorrow),
             "active_services": sum(0 < service.progress < 100 for service in services),
             "unscheduled": sum(not event.get("due_date") for event in pending)}
    if not todays and not overdue:
        text = "Na dziś nie masz otwartych terminów ani zaległości."
    else:
        text = f'Na dziś: {len(todays)} otwartych terminów. Zaległe terminy do sprawdzenia: {len(overdue)}.'
    if overdue:
        text += " Zacznij od sprawdzenia zaległości, a następnie przygotuj dzisiejsze spotkania."
    if stats["tomorrow"]:
        text += f' Na jutro zaplanowano {stats["tomorrow"]} terminów — warto się do nich przygotować.'
    if stats["unscheduled"]:
        text += f' Terminy bez ustalonej daty: {stats["unscheduled"]}.'
    return {"date": today.isoformat(), "stats": stats, "text": text, "source": "local",
            "ai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "today_events": todays[:5], "overdue_events": overdue[:3]}


def generate(stats, day):
    model = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini")
    # Only numeric counts and the date leave the application. No titles, clients,
    # IDs, notes, document contents, phone numbers or private links are sent.
    data = {"date": day, "counts": {key: int(stats[key]) for key in ("today", "overdue", "tomorrow", "active_services", "unscheduled")}}
    cache_key = hashlib.sha256(json.dumps([data, model], sort_keys=True).encode()).hexdigest()
    with _lock:
        cached = _cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        payload = {"model": model, "store": False, "max_output_tokens": 400,
                   "instructions": "Napisz po polsku krótkie podsumowanie dnia dla operatora CRM: 3–4 proste zdania, maksymalnie 100 słów, bez Markdown. Używaj wyłącznie podanych liczb. today oznacza otwarte terminy dzisiaj, overdue zaległe, tomorrow jutrzejsze, active_services usługi w trakcie, unscheduled terminy bez daty. Zasugeruj kolejność pracy: zaległości, dzisiejsze terminy, przygotowanie na jutro. Nie wymyślaj klientów, godzin, zdarzeń ani przyczyn. Nie twierdź, że cokolwiek wykonano lub wysłano. Jeśli wszystkie liczby są zerowe, powiedz, że nie ma spraw do podsumowania.",
                   "input": json.dumps(data, ensure_ascii=False)}
        request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), method="POST",
                          headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=25) as response:
                result = json.load(response)
            if result.get("status") != "completed":
                raise ValueError("Incomplete response")
            output = "\n".join(part["text"] for item in result.get("output", []) if item.get("type") == "message"
                               for part in item.get("content", []) if part.get("type") == "output_text").strip()
            if not output or len(output) > 2500:
                raise ValueError("Invalid output")
        except (HTTPError, URLError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError("AI jest teraz niedostępne. Pokazujemy zestawienie z danych aplikacji.") from exc
        _cache.clear()
        _cache[cache_key] = (time.monotonic(), output)
        return output
