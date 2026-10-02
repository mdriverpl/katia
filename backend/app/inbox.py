"""Read-only IMAP inbox and transactional attachment import."""
import hashlib
import imaplib
import os
import re
import ssl
from contextlib import contextmanager
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, getaddresses
from html.parser import HTMLParser
from io import BytesIO
from uuid import UUID, uuid4
from urllib.parse import quote

from fastapi import Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

MAX_MESSAGE = 20 * 1024 * 1024


class SettingsInput(BaseModel):
    host: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9.-]+$")
    port: int = Field(default=993, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=255)
    use_smtp_password: bool = True
    password: str | None = Field(default=None, max_length=2048)
    sender_filter: str = Field(default="", max_length=255)
    attachment_prefix: str = Field(default="", max_length=100)

    @field_validator("sender_filter")
    @classmethod
    def valid_sender(cls, value):
        value = value.strip().lower()
        if value and not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", value):
            raise ValueError("Podaj jeden poprawny adres nadawcy lub pozostaw pole puste")
        return value

    @field_validator("attachment_prefix")
    @classmethod
    def valid_prefix(cls, value):
        value = value.strip()
        if re.search(r'[\x00-\x1f\x7f/\\]', value):
            raise ValueError("Prefiks nie może zawierać znaków sterujących ani separatorów ścieżki")
        return value


class ImportInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_id: UUID
    document_type_id: UUID
    number: str = Field(min_length=1, max_length=100)
    attachments: list[int] = Field(min_length=1, max_length=10)


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.hidden += 1
        if tag in ("p", "br", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def parse_message(raw):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = message.get_body(preferencelist=("plain", "html"))
    content = ""
    if body is not None:
        payload = body.get_payload(decode=True) or b""
        try:
            content = payload.decode(body.get_content_charset() or "utf-8", errors="replace")
        except LookupError:
            content = payload.decode("utf-8", errors="replace")
        if body.get_content_type() == "text/html":
            parser = PlainHTML()
            parser.feed(content)
            content = "".join(parser.parts)
    attachments = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        if part.get_filename() or part.get_content_disposition() == "attachment":
            name = str(part.get_filename() or f"zalacznik-{index}").replace("\\", "/").split("/")[-1]
            name = re.sub(r"[\x00-\x1f\x7f]", "", name)[:255] or "zalacznik"
            data = part.get_payload(decode=True) or b""
            attachments.append({"id": index, "name": name, "size": len(data), "content": data})
    try:
        received = parsedate_to_datetime(str(message.get("Date", "")))
        if received.tzinfo is None:
            received = received.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        received = datetime.now(timezone.utc)
    return {"subject": str(message.get("Subject", "(bez tematu)"))[:500],
            "sender": str(message.get("From", ""))[:500], "received_at": received,
            "body": content, "attachments": attachments}


def smtp_values(api, db):
    return api.mail_config(db) or {key: os.getenv(key, "") for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD")}


def settings_view(api, db):
    row = db.get(api.InboxSettings, 1)
    smtp = smtp_values(api, db)
    boundary = db.get(api.InboxBoundary, 1)
    if not row:
        return {"host": smtp.get("SMTP_HOST", ""), "port": 993, "username": smtp.get("SMTP_USERNAME", ""),
                "use_smtp_password": True, "password_set": False, "configured": False,
                "sender_filter": "", "attachment_prefix": "", "sync_from": None}
    return {"host": row.host, "port": row.port, "username": row.username,
            "use_smtp_password": row.use_smtp_password,
            "password_set": bool(row.password_encrypted), "configured": True,
            "sender_filter": row.sender_filter, "attachment_prefix": row.attachment_prefix,
            "sync_from": boundary.started_at if boundary else None}


def eligible_attachment(name, prefix):
    return not prefix or name.casefold().startswith(prefix.casefold())


def mark_skipped(api, db, key):
    try:
        with db.begin_nested():
            db.add(api.InboxSkipped(message_id=key))
    except IntegrityError:
        pass


def checked(result):
    status, data = result
    if status != "OK":
        raise imaplib.IMAP4.error("Unexpected IMAP response")
    return data


@contextmanager
def connected_mailbox(api, db):
    # Serialize sync and changing the cutoff across API workers.
    row = db.scalar(select(api.InboxSettings).where(api.InboxSettings.id == 1).with_for_update())
    if not row:
        raise HTTPException(400, "Administrator musi zapisać ustawienia Poczta → IMAP.")
    password = smtp_values(api, db).get("SMTP_PASSWORD", "") if row.use_smtp_password else (
        api.fernet.decrypt(row.password_encrypted.encode()).decode() if row.password_encrypted else "")
    if not password:
        raise HTTPException(400, "Brak hasła do skrzynki. Sprawdź ustawienia Poczta → IMAP.")
    with imaplib.IMAP4_SSL(row.host, row.port, ssl_context=ssl.create_default_context(), timeout=20) as mailbox:
        checked(mailbox.login(row.username, password))
        checked(mailbox.select("INBOX", readonly=True))
        validity = mailbox.response("UIDVALIDITY")[1]
        if not validity or not validity[0]:
            raise imaplib.IMAP4.error("Missing UIDVALIDITY")
        namespace = hashlib.sha256(f"{row.host.lower()}:{row.port}:{row.username}:INBOX:{validity[0]!r}".encode()).hexdigest()
        yield row, mailbox, namespace


def start_from_now(api, db):
    try:
        with connected_mailbox(api, db) as (_, mailbox, namespace):
            # UIDNEXT is captured by SELECT: no message content or attachment is fetched.
            next_uid = mailbox.response("UIDNEXT")[1]
            if not next_uid or not next_uid[0] or int(next_uid[0]) < 1:
                raise imaplib.IMAP4.error("Missing UIDNEXT")
            boundary = db.get(api.InboxBoundary, 1)
            if boundary is None:
                boundary = api.InboxBoundary(id=1)
                db.add(boundary)
            boundary.namespace = namespace
            boundary.last_uid = int(next_uid[0]) - 1
            boundary.started_at = datetime.now(timezone.utc)
        db.commit()
        return {"sync_from": boundary.started_at}
    except (imaplib.IMAP4.error, OSError, ValueError) as cause:
        db.rollback()
        raise HTTPException(502, "Nie udało się ustawić odbioru od teraz. Sprawdź połączenie i ustawienia IMAP. Dotychczasowy zakres odbioru pozostaje bez zmian.") from cause


def sync_inbox(api, db):
    imported = skipped = filtered = consumed = 0
    try:
        with connected_mailbox(api, db) as (row, mailbox, namespace):
            boundary = db.get(api.InboxBoundary, 1)
            if boundary and boundary.namespace != namespace:
                raise HTTPException(409, "Zmieniła się skrzynka lub jej numeracja. W ustawieniach IMAP ponownie wybierz „Odbieraj tylko od teraz”.")
            criteria = ("FROM", f'"{row.sender_filter}"') if row.sender_filter else ("ALL",)
            if boundary:
                criteria = ("UID", f"{boundary.last_uid + 1}:*", *criteria)
            ids = checked(mailbox.uid("search", None, *criteria))[0].split()
            # IMAP ranges are inclusive and can reverse when '*' is smaller than the lower bound.
            if boundary:
                ids = [uid for uid in ids if int(uid) > boundary.last_uid]
            filter_key = "filter-" + hashlib.sha256(row.sender_filter.encode()).hexdigest() + "-"
            known = set(db.scalars(select(api.EmailMessage.message_id).where(api.EmailMessage.message_id.like(f"inbox-{namespace}-%"))))
            known.update(db.scalars(select(api.InboxSkipped.message_id).where(api.InboxSkipped.message_id.like(f"inbox-{namespace}-%"))))
            known.update(key[len(filter_key):] for key in db.scalars(select(api.InboxSkipped.message_id).where(api.InboxSkipped.message_id.like(f"{filter_key}inbox-{namespace}-%"))))
            pending = [uid for uid in reversed(ids) if f"inbox-{namespace}-{uid.decode()}" not in known]
            for uid in pending[:50]:
                size_data = checked(mailbox.uid("fetch", uid, "(RFC822.SIZE)"))
                match = re.search(rb"RFC822.SIZE\s+(\d+)", b" ".join(x for x in size_data if isinstance(x, bytes)))
                if not match:
                    raise imaplib.IMAP4.error("Missing size")
                size = int(match[1])
                if size > MAX_MESSAGE:
                    mark_skipped(api, db, f"inbox-{namespace}-{uid.decode()}")
                    skipped += 1
                    continue
                if consumed + size > 50 * 1024 * 1024:
                    break
                raw_data = checked(mailbox.uid("fetch", uid, "(BODY.PEEK[])"))
                raw = next((x[1] for x in raw_data if isinstance(x, tuple) and isinstance(x[1], bytes)), None)
                if raw is None:
                    raise imaplib.IMAP4.error("Missing body")
                if len(raw) > MAX_MESSAGE:
                    skipped += 1
                    continue
                consumed += len(raw)
                parsed = parse_message(raw)
                # IMAP FROM is a substring search, so verify the actual address too.
                headers = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
                senders = {address.casefold() for _, address in getaddresses([str(value) for value in headers.get_all("From", [])])}
                if row.sender_filter and row.sender_filter not in senders:
                    mark_skipped(api, db, f"{filter_key}inbox-{namespace}-{uid.decode()}")
                    filtered += 1
                    continue
                record = api.EmailMessage(id=uuid4(), message_id=f"inbox-{namespace}-{uid.decode()}",
                    sender=parsed["sender"], subject=parsed["subject"], received_at=parsed["received_at"], preview=parsed["body"][:1000])
                try:
                    with db.begin_nested():
                        db.add(record)
                        db.flush()
                        db.add(api.InboxContent(email_id=record.id, raw_encrypted=api.fernet.encrypt(raw)))
                    imported += 1
                except IntegrityError:
                    pass  # Another worker has already fetched this UID.
            db.commit()
            return {"imported": imported, "skipped": skipped, "filtered": filtered, "remaining": max(0, len(pending) - imported - skipped - filtered)}
    except (imaplib.IMAP4.error, OSError, ValueError) as cause:
        db.rollback()
        raise HTTPException(502, "Nie udało się odebrać poczty. Sprawdź serwer IMAP, login i hasło; spróbuj ponownie.") from cause


def content_for(api, db, email_id):
    content = db.get(api.InboxContent, email_id)
    if not content:
        raise HTTPException(404, "Ta wiadomość nie ma zapisanej pełnej treści. Odbierz pocztę ponownie.")
    return parse_message(api.fernet.decrypt(content.raw_encrypted))


def import_document(api, db, email_id, data):
    if not db.get(api.Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono firmy / klienta")
    kind = db.get(api.DocumentType, data.document_type_id)
    if not kind or kind.deleted_at:
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    parsed = content_for(api, db, email_id)
    selected = set(data.attachments)
    files = [item for item in parsed["attachments"] if item["id"] in selected]
    if len(files) != len(selected):
        raise HTTPException(400, "Nieprawidłowy załącznik")
    settings = db.get(api.InboxSettings, 1)
    prefix = settings.attachment_prefix if settings else ""
    if any(not eligible_attachment(item["name"], prefix) for item in files):
        raise HTTPException(400, "Wybrane pliki nie pasują do prefiksu w ustawieniach poczty. Odśwież wiadomość.")
    document = api.Document(id=uuid4(), company_id=data.company_id, document_type_id=kind.id,
                            title=kind.name, number=data.number, status="nowy")
    uploads = []
    try:
        db.add(document)
        for item in files:
            db.add(api.InboxImport(id=f"{email_id}:{item['id']}", email_id=email_id, document_id=document.id))
        db.flush()  # Unique receipts prevent simultaneous/repeated imports before writing S3.
        uploads = [UploadFile(filename=item["name"], file=BytesIO(item["content"])) for item in files]
        # Commits the document, receipts and files together; cleans up S3 on failure.
        api.upload_files(document.id, uploads, None, db)
        return {"id": document.id}
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(409, "Wybrany załącznik został już dodany do dokumentu. Odśwież wiadomość.") from cause
    except Exception:
        db.rollback()
        raise
    finally:
        for upload in uploads:
            upload.file.close()


def register(api):
    @api.app.post("/api/settings/inbox/start-now")
    def start_now(_=Depends(api.admin_user), db=Depends(api.db_session)):
        return start_from_now(api, db)

    @api.app.get("/api/settings/inbox")
    def get_settings(_=Depends(api.admin_user), db=Depends(api.db_session)):
        return settings_view(api, db)

    @api.app.put("/api/settings/inbox")
    def save_settings(data: SettingsInput, _=Depends(api.admin_user), db=Depends(api.db_session)):
        row = db.get(api.InboxSettings, 1)
        is_new = row is None
        if not row:
            row = api.InboxSettings(id=1)
            db.add(row)
        for key, value in data.model_dump(exclude={"password"}, exclude_unset=not is_new).items():
            setattr(row, key, value)
        if data.password is not None:
            row.password_encrypted = api.fernet.encrypt(data.password.encode()).decode() if data.password else None
        db.commit()
        return {"saved": True}

    @api.app.post("/api/inbox/sync")
    def sync(_=Depends(api.current_user), db=Depends(api.db_session)):
        return sync_inbox(api, db)

    @api.app.get("/api/inbox")
    def messages(offset: int = Query(0, ge=0), _=Depends(api.current_user), db=Depends(api.db_session)):
        rows = db.scalars(select(api.EmailMessage).order_by(api.EmailMessage.received_at.desc(), api.EmailMessage.id).offset(offset).limit(51)).all()
        return {"items": [{"id": row.id, "sender": row.sender, "subject": row.subject,
                           "received_at": row.received_at, "preview": row.preview[:200]} for row in rows[:50]], "has_more": len(rows) > 50}

    @api.app.get("/api/inbox/{email_id}")
    def detail(email_id: UUID, _=Depends(api.current_user), db=Depends(api.db_session)):
        row = db.get(api.EmailMessage, email_id)
        if not row:
            raise HTTPException(404, "Nie znaleziono wiadomości")
        if db.get(api.InboxContent, email_id):
            parsed = content_for(api, db, email_id)
        else:
            parsed = {"body": row.preview, "attachments": []}
        receipts = {item.id: item.document_id for item in db.scalars(select(api.InboxImport).where(api.InboxImport.email_id == email_id))}
        settings = db.get(api.InboxSettings, 1)
        prefix = settings.attachment_prefix if settings else ""
        return {"id": row.id, "sender": row.sender, "subject": row.subject, "received_at": row.received_at,
                "body": parsed["body"], "attachment_prefix": prefix,
                "attachments": [{**{key: item[key] for key in ("id", "name", "size")}, "eligible": eligible_attachment(item["name"], prefix),
                "document_id": receipts.get(f"{email_id}:{item['id']}")} for item in parsed["attachments"]]}

    @api.app.get("/api/inbox/{email_id}/attachments/{attachment_id}")
    def download(email_id: UUID, attachment_id: int, _=Depends(api.current_user), db=Depends(api.db_session)):
        parsed = content_for(api, db, email_id)
        item = next((item for item in parsed["attachments"] if item["id"] == attachment_id), None)
        if item is None:
            raise HTTPException(404, "Nie znaleziono załącznika")
        return Response(item["content"], media_type="application/octet-stream", headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(item['name'], safe='')}",
            "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

    @api.app.post("/api/inbox/{email_id}/documents")
    def create_document(email_id: UUID, data: ImportInput, _=Depends(api.current_user), db=Depends(api.db_session)):
        return import_document(api, db, email_id, data)
