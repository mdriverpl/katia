from __future__ import annotations

import base64
import hashlib
import imaplib
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from email import message_from_bytes
from uuid import UUID, uuid4

import jwt
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]
APP_SECRET = os.environ["APP_SECRET"]
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
security = HTTPBearer()
fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(APP_SECRET.encode()).digest()))


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255), index=True)
    nip: Mapped[str | None] = mapped_column(String(20))
    regon: Mapped[str | None] = mapped_column(String(20))
    pesel_encrypted: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    documents: Mapped[list[Document]] = relationship(back_populates="company")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(255))
    number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="nowy")
    due_date: Mapped[date | None] = mapped_column(Date)
    company: Mapped[Company] = relationship(back_populates="documents")


class Deadline(Base):
    __tablename__ = "deadlines"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="planowany")
    notes: Mapped[str | None] = mapped_column(Text)
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"))
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))


class EmailMessage(Base):
    __tablename__ = "email_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[str] = mapped_column(String(500), unique=True)
    sender: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preview: Mapped[str] = mapped_column(Text)


class LoginInput(BaseModel):
    email: str
    password: str


class CompanyInput(BaseModel):
    kind: str
    name: str
    nip: str | None = None
    regon: str | None = None
    pesel: str | None = None
    email: str | None = None
    phone: str | None = None


class CompanyOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    name: str
    nip: str | None
    regon: str | None
    email: str | None
    phone: str | None


class DocumentInput(BaseModel):
    company_id: UUID
    title: str
    number: str | None = None
    status: str = "nowy"
    due_date: date | None = None


class DeadlineInput(BaseModel):
    title: str
    due_date: date
    status: str = "planowany"
    notes: str | None = None
    company_id: UUID | None = None
    document_id: UUID | None = None


class ImapInput(BaseModel):
    host: str
    username: str
    password: str


def password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
    return base64.b64encode(salt + digest).decode()


def password_matches(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored)
    return hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 600000) == raw[16:]


def db_session():
    with SessionLocal() as db:
        yield db


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(db_session)) -> User:
    try:
        user_id = UUID(jwt.decode(credentials.credentials, APP_SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(401, "Nieprawidłowy token") from error
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Nieprawidłowy token")
    return user


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "admin@tms.local")):
            db.add(User(email="admin@tms.local", password_hash=password_hash("Admin123!")))
            db.commit()
    yield


app = FastAPI(title="TMS", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(data: LoginInput, db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not password_matches(data.password, user.password_hash):
        raise HTTPException(401, "Nieprawidłowy e-mail lub hasło")
    token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, APP_SECRET, algorithm="HS256")
    return {"access_token": token}


@app.get("/api/companies", response_model=list[CompanyOutput])
def companies(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Company).order_by(Company.name)).all()


@app.post("/api/companies", response_model=CompanyOutput)
def add_company(data: CompanyInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    values = data.model_dump(exclude={"pesel"})
    company = Company(**values, pesel_encrypted=fernet.encrypt(data.pesel.encode()).decode() if data.pesel else None)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@app.get("/api/documents")
def documents(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Document).order_by(Document.due_date)).all()


@app.post("/api/documents")
def add_document(data: DocumentInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    record = Document(**data.model_dump())
    db.add(record)
    db.commit()
    return {"id": record.id}


@app.get("/api/deadlines")
def deadlines(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Deadline).order_by(Deadline.due_date)).all()


@app.post("/api/deadlines")
def add_deadline(data: DeadlineInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    record = Deadline(**data.model_dump())
    db.add(record)
    db.commit()
    return {"id": record.id}


@app.get("/api/emails")
def emails(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(EmailMessage).order_by(EmailMessage.received_at.desc()).limit(50)).all()


@app.post("/api/emails/sync")
def sync_mail(data: ImapInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    try:
        mailbox = imaplib.IMAP4_SSL(data.host)
        mailbox.login(data.username, data.password)
        mailbox.select("INBOX", readonly=True)
        _, ids = mailbox.search(None, "ALL")
        imported = 0
        for message_number in ids[0].split()[-25:]:
            _, raw = mailbox.fetch(message_number, "(RFC822)")
            message = message_from_bytes(raw[0][1])
            message_id = message.get("Message-ID", f"imap-{message_number.decode()}")
            if db.scalar(select(EmailMessage).where(EmailMessage.message_id == message_id)):
                continue
            body = message.get_payload(decode=True)
            db.add(EmailMessage(message_id=message_id, sender=message.get("From", ""), subject=message.get("Subject", ""), received_at=datetime.now(timezone.utc), preview=body.decode(errors="replace")[:1000] if isinstance(body, bytes) else ""))
            imported += 1
        db.commit()
        mailbox.logout()
        return {"imported": imported}
    except imaplib.IMAP4.error as error:
        raise HTTPException(400, f"Błąd IMAP: {error}") from error
