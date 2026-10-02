from __future__ import annotations

import base64
import asyncio
import hashlib
import logging
import os
import re
import secrets
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4, uuid5
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlsplit
from typing import Literal

import jwt
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Header, Request
from fastapi.responses import Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, LargeBinary, BigInteger, Numeric, JSON, create_engine, select, delete, text, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError
from botocore.exceptions import BotoCoreError, ClientError
from .storage import storage_backend, s3_client, upload_bucket
from . import whatsapp, smsapi, daily_summary, account_mail, google_calendar

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
    role: Mapped[str] = mapped_column(String(20), default="employee", server_default="employee")
    blocked: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")


class MailSettings(Base):
    __tablename__ = "mail_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column()
    security: Mapped[str] = mapped_column(String(20))
    username: Mapped[str] = mapped_column(String(255))
    password_encrypted: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str] = mapped_column(String(255))
    public_url: Mapped[str] = mapped_column(String(2048))


class GoogleCalendarSettings(Base):
    __tablename__ = "google_calendar_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(String(255))
    client_secret_encrypted: Mapped[str] = mapped_column(Text)
    public_url: Mapped[str] = mapped_column(String(2048))
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    calendar_id: Mapped[str | None] = mapped_column(String(1024))
    namespace: Mapped[str] = mapped_column(String(32), default=lambda: uuid4().hex)
    automatic: Mapped[bool] = mapped_column(default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class GoogleCalendarOAuthState(Base):
    __tablename__ = "google_calendar_oauth_states"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column()
    token_version: Mapped[int] = mapped_column()
    verifier_encrypted: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255), index=True)
    nip: Mapped[str | None] = mapped_column(String(20))
    regon: Mapped[str | None] = mapped_column(String(20))
    pesel_encrypted: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(100))
    contact_type: Mapped[str | None] = mapped_column(String(100))
    residential_address: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    passport_number_encrypted: Mapped[str | None] = mapped_column(Text)
    employer_name: Mapped[str | None] = mapped_column(String(255))
    employer_email: Mapped[str | None] = mapped_column(String(255))
    employer_phone: Mapped[str | None] = mapped_column(String(50))
    documents: Mapped[list[Document]] = relationship(back_populates="company")


class ServicePublicLink(Base):
    __tablename__ = "service_public_links"
    service_id: Mapped[UUID] = mapped_column(ForeignKey("client_services.id"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_encrypted: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WhatsAppSubscription(Base):
    __tablename__ = "whatsapp_subscriptions"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)


class WhatsAppDelivery(Base):
    __tablename__ = "whatsapp_deliveries"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    message_id: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(20), default="whatsapp", server_default="whatsapp")


class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    default_method: Mapped[str] = mapped_column(String(20), default="whatsapp")
    automatic: Mapped[bool] = mapped_column(default=False)


class DocumentType(Base):
    __tablename__ = "document_types"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seed_name: Mapped[str | None] = mapped_column(String(100))


class DocumentTypeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)


class DocumentTypeOutput(DocumentTypeInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    document_type_id: Mapped[UUID | None] = mapped_column(ForeignKey("document_types.id"))
    title: Mapped[str] = mapped_column(String(255))
    number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="nowy")
    due_date: Mapped[date | None] = mapped_column(Date)
    terms: Mapped[list[dict] | None] = mapped_column(JSON)
    company: Mapped[Company] = relationship(back_populates="documents")


class DeadlineType(Base):
    __tablename__ = "deadline_types"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)
    client_calendar: Mapped[bool] = mapped_column(default=True)
    operator_calendar: Mapped[bool] = mapped_column(default=True)
    address: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))


class DeadlineTypeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    client_calendar: bool = True
    operator_calendar: bool = True
    address: str | None = Field(default=None, max_length=2000)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class DeadlineTypeOutput(DeadlineTypeInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


def deadline_type_key(name):
    return " ".join(name.split()).casefold()


def register_deadline_types(db, names):
    known = {item.name_key for item in db.scalars(select(DeadlineType))}
    for name in names:
        key = deadline_type_key(name)
        if key not in known:
            db.add(DeadlineType(name=name, name_key=key))
            known.add(key)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    deadline_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_details: Mapped[list[dict]] = mapped_column(JSON, default=list)


class ServiceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    description: str | None = None
    deadline_types: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("deadline_types")
    @classmethod
    def validate_types(cls, values):
        values = [value.strip() for value in values]
        if any(not value or len(value) > 100 for value in values):
            raise ValueError("Rodzaj terminu musi mieć od 1 do 100 znaków")
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError("Rodzaje terminów nie mogą się powtarzać")
        return values


class ServiceOutput(ServiceInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class TemplateDeadlineDetail(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    address: str | None = Field(default=None, max_length=2000)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ServiceTemplateInput(ServiceInput):
    deadline_details: list[TemplateDeadlineDetail] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_details(self):
        kinds = [item.kind for item in self.deadline_details]
        if len(kinds) != len(set(kinds)) or any(kind not in self.deadline_types for kind in kinds):
            raise ValueError("Dane terminu muszą odpowiadać rodzajom terminów usługi")
        return self


class ServiceTemplateOutput(ServiceTemplateInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class ClientService(Base):
    __tablename__ = "client_services"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(ForeignKey("services.id"))
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    deadline_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    appointments: Mapped[list[dict]] = mapped_column(JSON, default=list)
    progress: Mapped[int] = mapped_column(default=0)


class ServiceAppointment(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    due_date: date | None = None
    scheduled_time: str | None = Field(default=None, max_length=100)
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    completed: bool = False

    @model_validator(mode="after")
    def validate_time(self):
        if self.scheduled_time and not self.due_date:
            raise ValueError("Godzina wymaga podania daty")
        return self


class ClientServiceInput(BaseModel):
    template_id: UUID
    company_id: UUID
    appointments: list[ServiceAppointment] = Field(default_factory=list, max_length=30)


class ClientServiceUpdate(ServiceInput):
    company_id: UUID
    progress: int = Field(default=0, ge=0, le=100, strict=True)
    appointments: list[ServiceAppointment] | None = Field(default=None, max_length=30)


class ClientServiceOutput(ServiceOutput):
    template_id: UUID
    company_id: UUID
    created_at: datetime
    appointments: list[ServiceAppointment]
    progress: int


class Deadline(Base):
    __tablename__ = "deadlines"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="planowany")
    notes: Mapped[str | None] = mapped_column(Text)
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id"))
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("services.id"))
    deadline_types: Mapped[list[str] | None] = mapped_column(JSON, default=list)


class DocumentFile(Base):
    __tablename__ = "document_files"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    size: Mapped[int]
    s3_key: Mapped[str | None] = mapped_column(String(255))
    s3_bucket: Mapped[str | None] = mapped_column(String(255))


class DocumentFileOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    size: int


class DocumentTerm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=500)
    due_date: date
    calendar: Literal["client", "operator", "both"] = "both"


class DocumentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    document_type_id: UUID | None
    title: str
    number: str | None
    status: str
    due_date: date | None
    files: list[DocumentFileOutput] = Field(default_factory=list)
    terms: list[DocumentTerm] | None = None


class EmailMessage(Base):
    __tablename__ = "email_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[str] = mapped_column(String(500), unique=True)
    sender: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preview: Mapped[str] = mapped_column(Text)


class InboxSettings(Base):
    __tablename__ = "inbox_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int]
    username: Mapped[str] = mapped_column(String(255))
    use_smtp_password: Mapped[bool] = mapped_column(default=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text)
    sender_filter: Mapped[str] = mapped_column(String(255), default="", server_default="")
    attachment_prefix: Mapped[str] = mapped_column(String(100), default="", server_default="")


class InboxContent(Base):
    __tablename__ = "inbox_content"
    email_id: Mapped[UUID] = mapped_column(ForeignKey("email_messages.id"), primary_key=True)
    raw_encrypted: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)


class InboxBoundary(Base):
    __tablename__ = "inbox_boundary"
    id: Mapped[int] = mapped_column(primary_key=True)
    namespace: Mapped[str] = mapped_column(String(64))
    last_uid: Mapped[int] = mapped_column(BigInteger)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InboxImport(Base):
    __tablename__ = "inbox_imports"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    email_id: Mapped[UUID] = mapped_column(ForeignKey("email_messages.id"), index=True)
    # Keep the receipt after document deletion to prevent accidental duplicate import.
    document_id: Mapped[UUID]


class InboxSkipped(Base):
    __tablename__ = "inbox_skipped"
    message_id: Mapped[str] = mapped_column(String(500), primary_key=True)


class InboxCompleted(Base):
    __tablename__ = "inbox_completed"
    email_id: Mapped[UUID] = mapped_column(ForeignKey("email_messages.id"), primary_key=True)


class LoginInput(BaseModel):
    email: str
    password: str


class CompanyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    kind: str = "osoba"
    name: str = Field(default="", max_length=255)
    nip: str | None = None
    regon: str | None = None
    pesel: str | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    language: str | None = None
    contact_type: Literal["email", "phone", "whatsapp", "viber", "telegram"] | None = None
    residential_address: str | None = None
    birth_date: date | None = None
    passport_number: str | None = Field(default=None, max_length=100)
    employer_name: str | None = Field(default=None, max_length=255)
    employer_email: str | None = Field(default=None, max_length=255)
    employer_phone: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def person_name(self):
        self.kind = "osoba"
        if self.first_name and self.last_name:
            self.name = f"{self.first_name} {self.last_name}"
        elif not self.name:
            raise ValueError("Podaj imię i nazwisko klienta")
        return self

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value):
        if value and value > date.today():
            raise ValueError("Data urodzenia nie może być w przyszłości")
        return value


class CompanyOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    name: str
    nip: str | None
    regon: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    country: str | None
    language: str | None
    contact_type: str | None
    residential_address: str | None
    birth_date: date | None
    employer_name: str | None
    employer_email: str | None
    employer_phone: str | None


class CompanyDetailOutput(CompanyOutput):
    pesel: str | None
    passport_number: str | None


class DocumentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_id: UUID
    document_type_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    number: str | None = Field(default=None, max_length=100)
    status: str = Field(default="nowy", min_length=1, max_length=30)
    due_date: date | None = None
    terms: list[DocumentTerm] | None = Field(default=None, max_length=50)


class DeadlineInput(BaseModel):
    title: str
    due_date: date
    status: str = "planowany"
    notes: str | None = None
    company_id: UUID | None = None
    document_id: UUID | None = None
    service_id: UUID | None = None
    deadline_types: list[str] = Field(default_factory=list, max_length=30)


def password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
    return base64.b64encode(salt + digest).decode()


def password_matches(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored)
    return secrets.compare_digest(hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 600000), raw[16:])


def db_session():
    with SessionLocal() as db:
        yield db


def authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(db_session)) -> User:
    try:
        claims = jwt.decode(credentials.credentials, APP_SECRET, algorithms=["HS256"])
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(401, "Nieprawidłowy token") from error
    user = db.get(User, user_id)
    if not user or user.blocked or claims.get("version", 0) != user.token_version:
        raise HTTPException(401, "Nieprawidłowy token")
    return user


def current_user(user: User = Depends(authenticated_user)) -> User:
    if user.must_change_password:
        raise HTTPException(403, "Zmień hasło tymczasowe przed rozpoczęciem pracy")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Ta operacja wymaga uprawnień administratora")
    return user


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        inbox_columns = {column["name"] for column in inspect(connection).get_columns("inbox_settings")}
        for name, length in (("sender_filter", 255), ("attachment_prefix", 100)):
            if name not in inbox_columns:
                connection.execute(text(f"ALTER TABLE inbox_settings ADD COLUMN {name} VARCHAR({length}) NOT NULL DEFAULT ''"))
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        for name, definition in {
            "role": "VARCHAR(20) NOT NULL DEFAULT 'employee'",
            "blocked": "BOOLEAN NOT NULL DEFAULT false",
            "must_change_password": "BOOLEAN NOT NULL DEFAULT false",
            "token_version": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            if name not in user_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
        if "role" not in user_columns:
            connection.execute(text("UPDATE users SET role = 'admin' WHERE email = 'admin@tms.local'"))
        delivery_columns = {column["name"] for column in inspect(connection).get_columns("whatsapp_deliveries")}
        if "provider" not in delivery_columns:
            connection.execute(text("ALTER TABLE whatsapp_deliveries ADD COLUMN provider VARCHAR(20) NOT NULL DEFAULT 'whatsapp'"))
        file_columns = {column["name"] for column in inspect(connection).get_columns("document_files")}
        for column in ("s3_key", "s3_bucket"):
            if column not in file_columns:
                connection.execute(text(f"ALTER TABLE document_files ADD COLUMN {column} VARCHAR(255)"))
        existing = {column["name"] for column in inspect(connection).get_columns("companies")}
        for column in ("first_name", "last_name", "country", "language", "contact_type"):
            if column not in existing:
                connection.execute(text(f"ALTER TABLE companies ADD COLUMN {column} VARCHAR(100)"))
        if "residential_address" not in existing:
            connection.execute(text("ALTER TABLE companies ADD COLUMN residential_address TEXT"))
        if "birth_date" not in existing:
            connection.execute(text("ALTER TABLE companies ADD COLUMN birth_date DATE"))
        if "passport_number_encrypted" not in existing:
            connection.execute(text("ALTER TABLE companies ADD COLUMN passport_number_encrypted TEXT"))
        for column, length in (("employer_name", 255), ("employer_email", 255), ("employer_phone", 50)):
            if column not in existing:
                connection.execute(text(f"ALTER TABLE companies ADD COLUMN {column} VARCHAR({length})"))
        document_columns = {column["name"] for column in inspect(connection).get_columns("documents")}
        type_columns = {column["name"] for column in inspect(connection).get_columns("document_types")}
        if "deleted_at" not in type_columns:
            connection.execute(text("ALTER TABLE document_types ADD COLUMN deleted_at TIMESTAMP"))
        if "seed_name" not in type_columns:
            connection.execute(text("ALTER TABLE document_types ADD COLUMN seed_name VARCHAR(100)"))
        if "terms" not in document_columns:
            connection.execute(text("ALTER TABLE documents ADD COLUMN terms JSON"))
        if "document_type_id" not in document_columns:
            uuid_type = "UUID" if connection.dialect.name == "postgresql" else "CHAR(32)"
            connection.execute(text(f"ALTER TABLE documents ADD COLUMN document_type_id {uuid_type} REFERENCES document_types(id)"))
        deadline_columns = {column["name"] for column in inspect(connection).get_columns("deadlines")}
        if "service_id" not in deadline_columns:
            uuid_type = "UUID" if connection.dialect.name == "postgresql" else "CHAR(32)"
            connection.execute(text(f"ALTER TABLE deadlines ADD COLUMN service_id {uuid_type} REFERENCES services(id)"))
        if "deadline_types" not in deadline_columns:
            connection.execute(text("ALTER TABLE deadlines ADD COLUMN deadline_types JSON"))
        deadline_type_columns = {column["name"] for column in inspect(connection).get_columns("deadline_types")}
        if "amount" not in deadline_type_columns:
            connection.execute(text("ALTER TABLE deadline_types ADD COLUMN amount NUMERIC(12, 2)"))
        template_columns = {column["name"] for column in inspect(connection).get_columns("services")}
        if "deadline_details" not in template_columns:
            connection.execute(text("ALTER TABLE services ADD COLUMN deadline_details JSON NOT NULL DEFAULT '[]'"))
        if "deleted_at" not in template_columns:
            connection.execute(text("ALTER TABLE services ADD COLUMN deleted_at TIMESTAMP"))
        service_columns = {column["name"] for column in inspect(connection).get_columns("client_services")}
        if "appointments" not in service_columns:
            connection.execute(text("ALTER TABLE client_services ADD COLUMN appointments JSON NOT NULL DEFAULT '[]'"))
        if "progress" not in service_columns:
            connection.execute(text("ALTER TABLE client_services ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"))
    with SessionLocal() as db:
        known_types = {item.name_key for item in db.scalars(select(DeadlineType))}
        for model in (Service, ClientService, Deadline):
            for item in db.scalars(select(model)):
                for name in item.deadline_types or []:
                    key = deadline_type_key(name)
                    if key not in known_types:
                        db.add(DeadlineType(name=name, name_key=key))
                        known_types.add(key)
        for name in ("Paszport", "Karta pobytu", "Umowa najmu", "Prawo jazdy", "PESEL", "Akt urodzenia", "Akt małżeństwa", "Ubezpieczenie", "Meldunek", "Zdjęcie"):
            seeded = db.scalar(select(DocumentType).where((DocumentType.name_key == name.casefold()) | (DocumentType.seed_name == name)))
            if seeded:
                if seeded.seed_name is None:
                    seeded.seed_name = name
            else:
                db.add(DocumentType(name=name, name_key=name.casefold(), seed_name=name))
        kod95_id = UUID("fcf9394e-d124-4ac5-9544-b8a41964a6eb")
        if not db.get(Service, kod95_id) and not db.scalar(select(Service).where(Service.name == "KOD95")):
            db.add(Service(id=kod95_id, name="KOD95", price=None, description=None, deadline_types=[]))
        # Include existing dated documents once, including records created before this feature.
        for document in db.scalars(select(Document).where(Document.due_date.is_not(None), ~select(Deadline.id).where(Deadline.document_id == Document.id).exists())):
            db.add(Deadline(title=document.title, due_date=document.due_date, company_id=document.company_id, document_id=document.id, status="planowany"))
        if not db.scalar(select(User.id).limit(1)):
            db.add(User(email="admin@tms.local", password_hash=password_hash("Admin123!"), role="admin"))
        db.commit()
    whatsapp_stop = asyncio.Event()
    whatsapp_task = asyncio.create_task(whatsapp_loop(whatsapp_stop))
    google_task = asyncio.create_task(google_calendar_loop(whatsapp_stop))
    try:
        yield
    finally:
        whatsapp_stop.set()
        await whatsapp_task
        await google_task


app = FastAPI(title="TMS", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def public_privacy_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/public/", "/api/integrations/google-calendar")) or request.url.path.endswith("/public-link"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def link_is_active(link):
    return link and link.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


def public_service(x_client_token: str | None = Header(default=None), db: Session = Depends(db_session)) -> ClientService:
    if not x_client_token or len(x_client_token) > 100:
        raise HTTPException(404, "Link jest nieprawidłowy lub wygasł")
    digest = hashlib.sha256(x_client_token.encode()).hexdigest()
    link = db.scalar(select(ServicePublicLink).where(ServicePublicLink.token_hash == digest))
    if not link_is_active(link):
        raise HTTPException(404, "Link jest nieprawidłowy lub wygasł")
    service = db.get(ClientService, link.service_id)
    if not service or service.company_id != link.company_id:
        raise HTTPException(404, "Link jest nieprawidłowy lub wygasł")
    return service


@app.get("/api/client-services/{service_id}/public-link")
def get_public_link(service_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    service = db.get(ClientService, service_id)
    if not service:
        raise HTTPException(404, "Nie znaleziono usługi")
    link = db.get(ServicePublicLink, service_id)
    if not link_is_active(link) or link.company_id != service.company_id:
        return {"token": None, "expires_at": None}
    return {"token": fernet.decrypt(link.token_encrypted.encode()).decode(), "expires_at": link.expires_at.replace(tzinfo=timezone.utc)}


@app.post("/api/client-services/{service_id}/public-link")
def create_public_link(service_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    service = db.get(ClientService, service_id)
    if not service:
        raise HTTPException(404, "Nie znaleziono usługi")
    token = secrets.token_urlsafe(32)
    link = db.get(ServicePublicLink, service_id)
    values = {"company_id": service.company_id, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "token_encrypted": fernet.encrypt(token.encode()).decode(), "expires_at": datetime.now(timezone.utc) + timedelta(days=30)}
    if link:
        for key, value in values.items():
            setattr(link, key, value)
    else:
        link = ServicePublicLink(service_id=service_id, **values)
        db.add(link)
    db.commit()
    return {"token": token, "expires_at": link.expires_at.replace(tzinfo=timezone.utc)}


@app.delete("/api/client-services/{service_id}/public-link")
def revoke_public_link(service_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    if not db.get(ClientService, service_id):
        raise HTTPException(404, "Nie znaleziono usługi")
    link = db.get(ServicePublicLink, service_id)
    if link:
        db.delete(link)
        db.commit()
    return {"revoked": True}


@app.get("/api/public/service")
def public_service_data(response: Response, service: ClientService = Depends(public_service), db: Session = Depends(db_session)):
    company = db.get(Company, service.company_id)
    return {
        "client": {"id": company.id, "name": company.name},
        "deadlines": get_deadlines(db, service.company_id, include_unscheduled=True, audience="client"),
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(data: LoginInput, db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or user.blocked or not password_matches(data.password, user.password_hash):
        raise HTTPException(401, "Nieprawidłowy e-mail lub hasło")
    token = jwt.encode({"sub": str(user.id), "version": user.token_version, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, APP_SECRET, algorithm="HS256")
    return {"access_token": token}


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    role: Literal["admin", "employee"]
    blocked: bool
    must_change_password: bool


class UserInput(BaseModel):
    email: str = Field(max_length=255)
    role: Literal["admin", "employee"] = "employee"

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", value):
            raise ValueError("Podaj poprawny adres e-mail")
        return value


class UserUpdate(BaseModel):
    role: Literal["admin", "employee"]
    blocked: bool


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=128)


@app.get("/api/auth/me", response_model=UserOutput)
def me(user: User = Depends(authenticated_user)):
    return user


@app.post("/api/auth/password")
def change_password(data: PasswordInput, user: User = Depends(authenticated_user), db: Session = Depends(db_session)):
    # Serialize password changes so an old password cannot win a concurrent update.
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not password_matches(data.current_password, user.password_hash):
        raise HTTPException(400, "Obecne hasło jest nieprawidłowe")
    if password_matches(data.new_password, user.password_hash):
        raise HTTPException(400, "Nowe hasło musi różnić się od obecnego")
    user.password_hash = password_hash(data.new_password)
    user.must_change_password = False
    user.token_version += 1
    db.commit()
    return {"message": "Hasło zmienione. Zaloguj się ponownie."}


@app.get("/api/users", response_model=list[UserOutput])
def users(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    return db.scalars(select(User).order_by(User.email)).all()


@app.post("/api/users", response_model=UserOutput, status_code=201)
def add_user(data: UserInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    temporary_password = secrets.token_urlsafe(18)
    record = User(email=data.email, role=data.role, password_hash=password_hash(temporary_password), must_change_password=True)
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Użytkownik z tym adresem e-mail już istnieje")
    try:
        account_mail.send_welcome(record.email, temporary_password, mail_config(db))
    except Exception:
        db.rollback()
        raise HTTPException(502, "Nie udało się wysłać wiadomości. Konto nie zostało zapisane. Sprawdź konfigurację SMTP.")
    db.commit()
    return record


def managed_user(db, user_id, actor):
    # Lock accounts in a stable order to protect the last active administrator.
    records = db.scalars(select(User).order_by(User.id).with_for_update().execution_options(populate_existing=True)).all()
    if actor.role != "admin" or actor.blocked:
        raise HTTPException(403, "Brak uprawnień administratora")
    record = next((item for item in records if item.id == user_id), None)
    if not record:
        raise HTTPException(404, "Nie znaleziono użytkownika")
    if record.id == actor.id:
        raise HTTPException(400, "Nie możesz zmieniać uprawnień, blokować ani usuwać własnego konta")
    if record.role == "admin" and not record.blocked and sum(item.role == "admin" and not item.blocked for item in records) <= 1:
        raise HTTPException(400, "Musi pozostać co najmniej jeden aktywny administrator")
    return record


@app.put("/api/users/{user_id}", response_model=UserOutput)
def update_user(user_id: UUID, data: UserUpdate, actor: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = managed_user(db, user_id, actor)
    if record.role != data.role or record.blocked != data.blocked:
        record.token_version += 1
    record.role = data.role
    record.blocked = data.blocked
    db.commit()
    return record


@app.delete("/api/users/{user_id}")
def delete_user(user_id: UUID, actor: User = Depends(admin_user), db: Session = Depends(db_session)):
    db.delete(managed_user(db, user_id, actor))
    db.commit()
    return {"deleted": True}


class MailSettingsInput(BaseModel):
    host: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9.-]+$")
    port: int = Field(ge=1, le=65535)
    security: Literal["starttls", "ssl"] = "starttls"
    username: str = Field(default="", max_length=255)
    password: str | None = Field(default=None, max_length=2048)
    sender: str = Field(max_length=255)
    public_url: str = Field(default="", max_length=2048)

    @field_validator("host", "username", "sender", "public_url", mode="before")
    @classmethod
    def trim_addresses(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("sender")
    @classmethod
    def valid_sender(cls, value):
        return UserInput.valid_email(value)

    @field_validator("public_url")
    @classmethod
    def valid_url(cls, value):
        value = value.strip().rstrip("/")
        if value and (not value.startswith("https://") or any(char.isspace() for char in value)):
            raise ValueError("Podaj adres HTTPS panelu")
        return value


def mail_config(db):
    settings = db.get(MailSettings, 1)
    if not settings:
        return None
    return {"SMTP_HOST": settings.host, "SMTP_PORT": settings.port, "SMTP_SECURITY": settings.security,
            "SMTP_USERNAME": settings.username, "SMTP_PASSWORD": fernet.decrypt(settings.password_encrypted.encode()).decode() if settings.password_encrypted else "",
            "SMTP_FROM": settings.sender, "PUBLIC_APP_URL": settings.public_url}


@app.get("/api/settings/mail")
def get_mail_settings(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    settings = db.get(MailSettings, 1)
    if not settings:
        return {"host": os.getenv("SMTP_HOST", ""), "port": int(os.getenv("SMTP_PORT", "587")),
                "security": os.getenv("SMTP_SECURITY", "starttls"), "username": os.getenv("SMTP_USERNAME", ""),
                "sender": os.getenv("SMTP_FROM", ""), "public_url": os.getenv("PUBLIC_APP_URL", ""),
                "password_set": bool(os.getenv("SMTP_PASSWORD"))}
    return {**{key: getattr(settings, key) for key in ("host", "port", "security", "username", "sender", "public_url")},
            "password_set": bool(settings.password_encrypted)}


@app.put("/api/settings/mail")
def save_mail_settings(data: MailSettingsInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    settings = db.get(MailSettings, 1)
    if not settings:
        settings = MailSettings(id=1)
        initial_password = os.getenv("SMTP_PASSWORD", "")
        settings.password_encrypted = fernet.encrypt(initial_password.encode()).decode() if initial_password else None
        db.add(settings)
    for key, value in data.model_dump(exclude={"password"}).items():
        setattr(settings, key, value)
    if data.password is not None:
        settings.password_encrypted = fernet.encrypt(data.password.encode()).decode() if data.password else None
    db.commit()
    return {"saved": True}


class GoogleCalendarInput(BaseModel):
    client_id: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9._-]+$")
    client_secret: str | None = Field(default=None, max_length=2048)
    public_url: str = Field(max_length=2048)
    automatic: bool = True

    @field_validator("public_url")
    @classmethod
    def valid_origin(cls, value):
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        local = parsed.hostname in ("localhost", "127.0.0.1")
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or any(char.isspace() for char in value):
            raise ValueError("Podaj adres panelu bez ścieżki i parametrów")
        if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
            raise ValueError("Adres panelu musi używać HTTPS (lokalnie można użyć HTTP)")
        return value


google_sync_lock = threading.Lock()


@contextmanager
def locked_google_settings(db):
    if not google_sync_lock.acquire(blocking=False):
        raise HTTPException(409, "Trwa operacja Kalendarza Google. Spróbuj za chwilę.")
    try:
        settings = db.scalar(select(GoogleCalendarSettings).where(GoogleCalendarSettings.id == 1).with_for_update(skip_locked=True).execution_options(populate_existing=True))
        if not settings and db.get(GoogleCalendarSettings, 1):
            raise HTTPException(409, "Trwa operacja Kalendarza Google. Spróbuj za chwilę.")
        yield settings
    finally:
        google_sync_lock.release()


@app.get("/api/integrations/google-calendar")
def google_calendar_settings(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    settings = db.get(GoogleCalendarSettings, 1)
    if not settings:
        return {"client_id": "", "public_url": "", "client_secret_set": False, "connected": False,
                "automatic": True, "calendar_id": None, "last_synced_at": None, "last_error": None}
    return {"client_id": settings.client_id, "public_url": settings.public_url,
            "client_secret_set": bool(settings.client_secret_encrypted), "connected": bool(settings.refresh_token_encrypted and settings.calendar_id),
            "automatic": settings.automatic, "calendar_id": settings.calendar_id,
            "last_synced_at": settings.last_synced_at, "last_error": settings.last_error}


def clear_google_states(db):
    for state in db.scalars(select(GoogleCalendarOAuthState)):
        db.delete(state)


@app.put("/api/integrations/google-calendar")
def save_google_calendar(data: GoogleCalendarInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    with locked_google_settings(db) as settings:
        if settings and settings.refresh_token_encrypted and data.client_id != settings.client_id:
            raise HTTPException(400, "Rozłącz konto przed zmianą Client ID")
        if not settings:
            if not data.client_secret:
                raise HTTPException(400, "Podaj Client Secret z Google Cloud")
            settings = GoogleCalendarSettings(id=1)
            db.add(settings)
        settings.client_id = data.client_id
        settings.public_url = data.public_url
        settings.automatic = data.automatic
        if data.client_secret:
            settings.client_secret_encrypted = fernet.encrypt(data.client_secret.encode()).decode()
        clear_google_states(db)
        db.commit()
    return {"saved": True}


@app.post("/api/integrations/google-calendar/connect")
def connect_google_calendar(response: Response, user: User = Depends(admin_user), db: Session = Depends(db_session)):
    with locked_google_settings(db) as settings:
        if not settings:
            raise HTTPException(400, "Najpierw zapisz konfigurację Google OAuth")
        clear_google_states(db)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        db.add(GoogleCalendarOAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(), user_id=user.id,
            token_version=user.token_version, verifier_encrypted=fernet.encrypt(verifier.encode()).decode(),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        url = google_calendar.authorization_url(settings.client_id, settings.public_url + google_calendar.CALLBACK_PATH, state, verifier)
        response.set_cookie("google_calendar_state", state, max_age=600, httponly=True,
                            secure=settings.public_url.startswith("https://"), samesite="lax", path=google_calendar.CALLBACK_PATH)
        db.commit()
    return {"url": url}


@app.get(google_calendar.CALLBACK_PATH)
def google_calendar_callback(request: Request, state: str = "", code: str = "", error: str = "", db: Session = Depends(db_session)):
    cookie = request.cookies.get("google_calendar_state", "")
    if not state or not cookie or len(state) > 200 or not secrets.compare_digest(state, cookie):
        raise HTTPException(400, "Nieprawidłowe potwierdzenie Google. Rozpocznij łączenie ponownie w Ustawieniach.")
    with locked_google_settings(db) as settings:
        pending = db.get(GoogleCalendarOAuthState, hashlib.sha256(state.encode()).hexdigest())
        if not settings or not pending or pending.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(400, "Połączenie Google wygasło lub zostało już wykorzystane")
        owner = db.get(User, pending.user_id)
        if not owner or owner.blocked or owner.role != "admin" or owner.must_change_password or owner.token_version != pending.token_version:
            raise HTTPException(403, "Sesja administratora nie jest już aktywna. Zaloguj się ponownie.")
        verifier = fernet.decrypt(pending.verifier_encrypted.encode()).decode()
        db.delete(pending)
        result = "connected"
        try:
            if error or not code:
                raise google_calendar.GoogleError("Nie udzielono zgody na połączenie Kalendarza Google.")
            credentials = google_calendar.exchange_code(settings.client_id,
                fernet.decrypt(settings.client_secret_encrypted.encode()).decode(),
                settings.public_url + google_calendar.CALLBACK_PATH, code, verifier)
            calendar_id = settings.calendar_id
            if calendar_id:
                try:
                    google_calendar.request("GET", google_calendar.API + "/calendars/" + quote(calendar_id, safe=""), token=credentials["access_token"])
                except google_calendar.GoogleError as cause:
                    if cause.status not in (403, 404, 410):
                        raise
                    calendar_id = None
            if not calendar_id:
                calendar_id = google_calendar.create_calendar(credentials["access_token"])
            settings.calendar_id = calendar_id
            settings.refresh_token_encrypted = fernet.encrypt(credentials["refresh_token"].encode()).decode()
            settings.last_error = None
        except google_calendar.GoogleError as cause:
            settings.last_error = str(cause)
            result = "error"
        redirect = RedirectResponse(settings.public_url + "/?google_calendar=" + result, status_code=303)
        redirect.delete_cookie("google_calendar_state", path=google_calendar.CALLBACK_PATH)
        redirect.headers["Cache-Control"] = "no-store"
        redirect.headers["Referrer-Policy"] = "no-referrer"
        db.commit()
    return redirect


@app.delete("/api/integrations/google-calendar/connection")
def disconnect_google_calendar(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    with locked_google_settings(db) as settings:
        warning = None
        if settings:
            if settings.refresh_token_encrypted:
                try:
                    google_calendar.request("POST", "https://oauth2.googleapis.com/revoke",
                        {"token": fernet.decrypt(settings.refresh_token_encrypted.encode()).decode()}, form=True)
                except google_calendar.GoogleError:
                    warning = "Synchronizacja wyłączona. Cofnięcie zgody w Google nie zostało potwierdzone; możesz usunąć dostęp w ustawieniach konta Google."
            settings.refresh_token_encrypted = None
            settings.calendar_id = None
            settings.automatic = False
            settings.last_synced_at = None
            settings.last_error = None
        clear_google_states(db)
        db.commit()
    return {"disconnected": True, "warning": warning}


def run_google_sync(db, automatic=False):
    with locked_google_settings(db) as settings:
        if not settings or not settings.refresh_token_encrypted or not settings.calendar_id:
            if automatic:
                return {"skipped": True}
            raise HTTPException(400, "Najpierw połącz Kalendarz Google")
        if automatic and (not settings.automatic or (settings.last_synced_at and settings.last_synced_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(minutes=5))):
            return {"skipped": True}
        try:
            token = google_calendar.refresh_access(settings.client_id, fernet.decrypt(settings.client_secret_encrypted.encode()).decode(),
                fernet.decrypt(settings.refresh_token_encrypted.encode()).decode())
            events = get_deadlines(db, audience="operator")
            clients = {client.id: client.name for client in db.scalars(select(Company))}
            result = google_calendar.sync_events(token, settings.calendar_id, settings.namespace, events, clients)
            settings.last_synced_at = datetime.now(timezone.utc)
            settings.last_error = None
        except google_calendar.GoogleError as cause:
            settings.last_error = str(cause)
            db.commit()
            raise HTTPException(502, str(cause)) from None
        db.commit()
    return result


@app.post("/api/integrations/google-calendar/sync")
def sync_google_calendar(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    return run_google_sync(db)


def google_sync_tick():
    with SessionLocal() as db:
        try:
            run_google_sync(db, automatic=True)
        except HTTPException:
            pass  # Provider errors are recorded in the settings panel; another worker may hold the lock.


async def google_calendar_loop(stop):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=300)
        except asyncio.TimeoutError:
            try:
                await asyncio.to_thread(google_sync_tick)
            except Exception:
                logging.getLogger(__name__).error("Google Calendar background sync failed")


@app.get("/api/companies", response_model=list[CompanyOutput])
def companies(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Company).order_by(Company.name)).all()


@app.post("/api/companies", response_model=CompanyOutput)
def add_company(data: CompanyInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    values = data.model_dump(exclude={"pesel", "passport_number"})
    company = Company(**values, pesel_encrypted=fernet.encrypt(data.pesel.encode()).decode() if data.pesel else None, passport_number_encrypted=fernet.encrypt(data.passport_number.encode()).decode() if data.passport_number else None)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@app.get("/api/companies/{company_id}", response_model=CompanyDetailOutput)
def company_details(company_id: UUID, response: Response, _: User = Depends(current_user), db: Session = Depends(db_session)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Nie znaleziono klienta")
    response.headers["Cache-Control"] = "no-store"
    values = CompanyOutput.model_validate(company).model_dump()
    return {**values, "pesel": fernet.decrypt(company.pesel_encrypted.encode()).decode() if company.pesel_encrypted else None, "passport_number": fernet.decrypt(company.passport_number_encrypted.encode()).decode() if company.passport_number_encrypted else None}


@app.put("/api/companies/{company_id}", response_model=CompanyOutput)
def update_company(company_id: UUID, data: CompanyInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Nie znaleziono klienta")
    for key, value in data.model_dump(exclude={"pesel", "passport_number"}).items():
        setattr(company, key, value)
    # Omitted PESEL preserves the encrypted value; an explicit empty value clears it.
    if "pesel" in data.model_fields_set:
        company.pesel_encrypted = fernet.encrypt(data.pesel.encode()).decode() if data.pesel else None
    if "passport_number" in data.model_fields_set:
        company.passport_number_encrypted = fernet.encrypt(data.passport_number.encode()).decode() if data.passport_number else None
    db.commit()
    db.refresh(company)
    return company


@app.delete("/api/companies/{company_id}")
def delete_company(company_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    company = db.scalar(select(Company).where(Company.id == company_id).with_for_update())
    if not company:
        raise HTTPException(404, "Nie znaleziono klienta")
    document_ids = select(Document.id).where(Document.company_id == company_id)
    service_ids = select(ClientService.id).where(ClientService.company_id == company_id)
    objects = list(db.execute(select(DocumentFile.s3_bucket, DocumentFile.s3_key).where(
        DocumentFile.document_id.in_(document_ids), DocumentFile.s3_key.is_not(None))))
    # Delete dependencies in one transaction before removing the client.
    db.execute(delete(ServicePublicLink).where((ServicePublicLink.company_id == company_id) | ServicePublicLink.service_id.in_(service_ids)))
    db.execute(delete(WhatsAppSubscription).where(WhatsAppSubscription.company_id == company_id))
    db.execute(delete(WhatsAppDelivery).where(WhatsAppDelivery.company_id == company_id))
    db.execute(delete(DocumentFile).where(DocumentFile.document_id.in_(document_ids)))
    db.execute(delete(Deadline).where((Deadline.company_id == company_id) | Deadline.document_id.in_(document_ids)))
    db.execute(delete(ClientService).where(ClientService.company_id == company_id))
    db.execute(delete(Document).where(Document.company_id == company_id))
    db.execute(delete(Company).where(Company.id == company_id))
    db.commit()
    cleanup_failed = False
    for bucket, key in objects:
        try:
            s3_client().delete_object(Bucket=bucket, Key=key)
        except Exception:
            cleanup_failed = True
            logging.getLogger(__name__).error("S3 cleanup failed for deleted client %s, bucket %s, key %s", company_id, bucket, key)
    return {"deleted": True, "cleanup_warning": "Klienta usunięto, ale nie udało się usunąć wszystkich plików z S3. Sprawdź logi serwera." if cleanup_failed else None}


@app.get("/api/deadline-types", response_model=list[DeadlineTypeOutput])
def deadline_types(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(DeadlineType).order_by(DeadlineType.name)).all()


@app.post("/api/deadline-types", response_model=DeadlineTypeOutput)
def add_deadline_type(data: DeadlineTypeInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = DeadlineType(**data.model_dump(), name_key=deadline_type_key(data.name))
    db.add(record)
    return save_deadline_type(db, record)


def save_deadline_type(db, record):
    try:
        db.commit()
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(409, "Taki rodzaj terminu już istnieje") from cause
    db.refresh(record)
    return record


@app.put("/api/deadline-types/{type_id}", response_model=DeadlineTypeOutput)
def update_deadline_type(type_id: UUID, data: DeadlineTypeInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = db.get(DeadlineType, type_id)
    if not record:
        raise HTTPException(404, "Nie znaleziono rodzaju terminu")
    key = deadline_type_key(data.name)
    if db.scalar(select(DeadlineType).where(DeadlineType.name_key == key, DeadlineType.id != type_id)):
        raise HTTPException(409, "Taki rodzaj terminu już istnieje")
    old_key = record.name_key
    if record.name != data.name:
        for model in (Service, ClientService, Deadline):
            for item in db.scalars(select(model)):
                item.deadline_types = [data.name if deadline_type_key(name) == old_key else name for name in item.deadline_types or []]
                if isinstance(item, Service):
                    item.deadline_details = [{**entry, "kind": data.name} if deadline_type_key(entry["kind"]) == old_key else entry for entry in item.deadline_details]
                if isinstance(item, ClientService):
                    item.appointments = [{**entry, "kind": data.name} if deadline_type_key(entry["kind"]) == old_key else entry for entry in item.appointments]
    for field, value in data.model_dump().items():
        setattr(record, field, value)
    record.name_key = key
    return save_deadline_type(db, record)


@app.get("/api/document-types", response_model=list[DocumentTypeOutput])
def document_types(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(DocumentType).where(DocumentType.deleted_at.is_(None)).order_by(DocumentType.name)).all()


@app.post("/api/document-types", response_model=DocumentTypeOutput)
def add_document_type(data: DocumentTypeInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    name = " ".join(data.name.split())
    record = db.scalar(select(DocumentType).where(DocumentType.name_key == name.casefold()))
    if record and not record.deleted_at:
        raise HTTPException(409, "Taki rodzaj dokumentu już istnieje")
    if record:
        record.name = name
        record.deleted_at = None
    else:
        record = DocumentType(name=name, name_key=name.casefold())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(409, "Taki rodzaj dokumentu już istnieje") from cause
    db.refresh(record)
    return record


@app.put("/api/document-types/{type_id}", response_model=DocumentTypeOutput)
def update_document_type(type_id: UUID, data: DocumentTypeInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = db.get(DocumentType, type_id)
    if not record or record.deleted_at:
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    name = " ".join(data.name.split())
    record.name = name
    record.name_key = name.casefold()
    try:
        db.commit()
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(409, "Taki rodzaj dokumentu już istnieje") from cause
    db.refresh(record)
    return record


@app.delete("/api/document-types/{type_id}")
def delete_document_type(type_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = db.get(DocumentType, type_id)
    if not record or record.deleted_at:
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    for document in db.scalars(select(Document).where(Document.document_type_id == type_id)):
        document.document_type_id = None
    record.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"deleted": True}


def valid_document_type(db, type_id):
    record = db.get(DocumentType, type_id)
    return record and not record.deleted_at


@app.get("/api/documents", response_model=list[DocumentOutput])
def documents(_: User = Depends(current_user), db: Session = Depends(db_session)):
    files = {}
    for attachment in db.scalars(select(DocumentFile)):
        files.setdefault(attachment.document_id, []).append(DocumentFileOutput.model_validate(attachment))
    return [DocumentOutput.model_validate(document).model_copy(update={"files": files.get(document.id, [])}) for document in db.scalars(select(Document).order_by(Document.due_date))]


@app.post("/api/documents")
def add_document(data: DocumentInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    if not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    if data.document_type_id and not valid_document_type(db, data.document_type_id):
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    values = data.model_dump(exclude={"terms"})
    if data.terms is not None:
        values["due_date"] = None
    record = Document(**values, terms=[term.model_dump(mode="json") for term in data.terms] if data.terms is not None else None)
    db.add(record)
    db.flush()
    if record.due_date:
        db.add(Deadline(title=record.title, due_date=record.due_date, company_id=record.company_id, document_id=record.id, status="planowany"))
    db.commit()
    return {"id": record.id}


@app.put("/api/documents/{document_id}")
def update_document(document_id: UUID, data: DocumentInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    record = db.get(Document, document_id)
    if not record:
        raise HTTPException(404, "Nie znaleziono dokumentu")
    if not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    if data.document_type_id and not valid_document_type(db, data.document_type_id):
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    for key, value in data.model_dump(exclude={"terms"}).items():
        setattr(record, key, value)
    if "terms" in data.model_fields_set:
        record.terms = [term.model_dump(mode="json") for term in data.terms] if data.terms is not None else None
    if record.terms is not None:
        record.due_date = None
    for event in db.scalars(select(Deadline).where(Deadline.document_id == document_id)):
        db.delete(event)
    if record.due_date:
        db.add(Deadline(title=record.title, due_date=record.due_date, company_id=record.company_id, document_id=record.id, status="planowany"))
    db.commit()
    return {"id": record.id}


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    record = db.get(Document, document_id)
    if not record:
        raise HTTPException(404, "Nie znaleziono dokumentu")
    attachments = db.scalars(select(DocumentFile).where(DocumentFile.document_id == document_id)).all()
    objects = [(item.s3_bucket, item.s3_key) for item in attachments if item.s3_key]
    for attachment in attachments:
        db.delete(attachment)
    for event in db.scalars(select(Deadline).where(Deadline.document_id == document_id)):
        db.delete(event)
    db.flush()
    db.delete(record)
    db.commit()
    cleanup_failed = False
    for bucket, key in objects:
        try:
            s3_client().delete_object(Bucket=bucket, Key=key)
        except Exception:
            cleanup_failed = True
            logging.getLogger(__name__).error("S3 cleanup failed for deleted document %s, bucket %s, key %s", document_id, bucket, key)
    return {"deleted": True, "cleanup_warning": "Dokument usunięto, ale nie udało się usunąć wszystkich plików z S3. Sprawdź logi serwera." if cleanup_failed else None}


@app.post("/api/documents/{document_id}/files", response_model=list[DocumentFileOutput])
def upload_files(document_id: UUID, files: list[UploadFile] = File(...), _: User = Depends(current_user), db: Session = Depends(db_session)):
    if not db.get(Document, document_id):
        raise HTTPException(404, "Nie znaleziono dokumentu")
    if not 1 <= len(files) <= 10:
        raise HTTPException(400, "Wybierz od 1 do 10 plików")
    attachments = []
    for upload in files:
        content = upload.file.read(20 * 1024 * 1024 + 1)
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "Maksymalny rozmiar pliku to 20 MB")
        name = (upload.filename or "plik").replace("\\", "/").split("/")[-1][:255] or "plik"
        attachments.append(DocumentFile(id=uuid4(), document_id=document_id, name=name, content=content, size=len(content)))
    uploaded = []
    client = None
    try:
        if storage_backend() == "s3":
            bucket = upload_bucket()
            client = s3_client()
            for attachment in attachments:
                key = f"documents/{document_id}/{attachment.id}"
                # Record the attempted key too: a timeout can occur after S3 stores it.
                uploaded.append((bucket, key))
                client.put_object(Bucket=bucket, Key=key, Body=attachment.content, ContentType="application/octet-stream")
                attachment.s3_bucket = bucket
                attachment.s3_key = key
                attachment.content = b""
        db.add_all(attachments)
        db.commit()
    except Exception as cause:
        db.rollback()
        for bucket, key in uploaded:
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception:
                logging.getLogger(__name__).error("Nie udało się posprzątać pliku S3: %s", key)
        if isinstance(cause, (BotoCoreError, ClientError)):
            raise HTTPException(502, "Nie udało się zapisać plików w S3. Spróbuj ponownie.") from cause
        raise
    return attachments


@app.get("/api/documents/{document_id}/files/{file_id}")
def download_file(document_id: UUID, file_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    attachment = db.get(DocumentFile, file_id)
    if not attachment or attachment.document_id != document_id:
        raise HTTPException(404, "Nie znaleziono pliku")
    if attachment.s3_key:
        try:
            result = s3_client().get_object(Bucket=attachment.s3_bucket, Key=attachment.s3_key)
            try:
                content = result["Body"].read()
            finally:
                result["Body"].close()
        except (BotoCoreError, ClientError) as cause:
            raise HTTPException(502, "Nie udało się pobrać pliku z S3. Spróbuj ponownie.") from cause
    else:
        content = attachment.content
    return Response(content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.name, safe='')}", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@app.get("/api/services", response_model=list[ServiceTemplateOutput])
@app.get("/api/service-types", response_model=list[ServiceTemplateOutput])
def services(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Service).where(Service.deleted_at.is_(None)).order_by(Service.name)).all()


@app.post("/api/services", response_model=ServiceTemplateOutput)
@app.post("/api/service-types", response_model=ServiceTemplateOutput)
def add_service(data: ServiceTemplateInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    register_deadline_types(db, data.deadline_types)
    service = Service(**data.model_dump(exclude={"deadline_details"}), deadline_details=[item.model_dump(mode="json") for item in data.deadline_details])
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@app.put("/api/services/{service_id}", response_model=ServiceTemplateOutput)
@app.put("/api/service-types/{service_id}", response_model=ServiceTemplateOutput)
def update_service(service_id: UUID, data: ServiceTemplateInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    service = db.get(Service, service_id)
    if not service or service.deleted_at:
        raise HTTPException(404, "Nie znaleziono usługi")
    register_deadline_types(db, data.deadline_types)
    service.deadline_details = [item.model_dump(mode="json") for item in data.deadline_details] if "deadline_details" in data.model_fields_set else [item for item in service.deadline_details if item["kind"] in data.deadline_types]
    for key, value in data.model_dump(exclude={"deadline_details"}).items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@app.delete("/api/services/{service_id}")
@app.delete("/api/service-types/{service_id}")
def delete_service(service_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    service = db.get(Service, service_id)
    if not service or service.deleted_at:
        raise HTTPException(404, "Nie znaleziono rodzaju usługi")
    # Preserve references from existing client services and appointments.
    service.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"deleted": True}


@app.get("/api/client-services", response_model=list[ClientServiceOutput])
def client_services(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(ClientService).order_by(ClientService.created_at.desc(), ClientService.id)).all()


@app.post("/api/client-services", response_model=ClientServiceOutput)
def add_client_service(data: ClientServiceInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    template = db.get(Service, data.template_id)
    if not template or template.deleted_at:
        raise HTTPException(404, "Nie znaleziono rodzaju usługi")
    if not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    appointments = validate_appointments(data.appointments, template.deadline_types)
    service = ClientService(template_id=template.id, company_id=data.company_id, name=template.name, price=template.price, description=template.description, deadline_types=list(template.deadline_types), appointments=appointments)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def validate_appointments(appointments, kinds):
    names = [item.kind for item in appointments]
    if len(names) != len(set(names)) or any(name not in kinds for name in names):
        raise HTTPException(400, "Każdy termin musi mieć unikalny rodzaj należący do usługi")
    return [item.model_dump(mode="json") for item in appointments]


@app.put("/api/client-services/{service_id}", response_model=ClientServiceOutput)
def update_client_service(service_id: UUID, data: ClientServiceUpdate, _: User = Depends(current_user), db: Session = Depends(db_session)):
    service = db.get(ClientService, service_id)
    if not service:
        raise HTTPException(404, "Nie znaleziono usługi klienta")
    if not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    appointments = data.appointments if data.appointments is not None else [ServiceAppointment(**item) for item in service.appointments if item["kind"] in data.deadline_types]
    service.appointments = validate_appointments(appointments, data.deadline_types)
    register_deadline_types(db, data.deadline_types)
    if service.company_id != data.company_id:
        link = db.get(ServicePublicLink, service.id)
        if link:
            db.delete(link)
    for key, value in data.model_dump(exclude={"appointments"}).items():
        if key == "progress" and key not in data.model_fields_set:
            continue
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@app.get("/api/deadlines")
def deadlines(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return get_deadlines(db)


@app.get("/api/companies/{company_id}/deadlines")
def company_deadlines(company_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    if not db.get(Company, company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    return get_deadlines(db, company_id, include_unscheduled=True, audience="all")


def get_deadlines(db: Session, company_id: UUID | None = None, include_unscheduled: bool = False, audience: str = "operator"):
    deadline_query = select(Deadline)
    service_query = select(ClientService)
    if company_id is not None:
        deadline_query = deadline_query.where(Deadline.company_id == company_id)
        service_query = service_query.where(ClientService.company_id == company_id)
    records = [{column.name: getattr(item, column.name) for column in Deadline.__table__.columns} for item in db.scalars(deadline_query)]
    document_query = select(Document)
    if company_id is not None:
        document_query = document_query.where(Document.company_id == company_id)
    for document in db.scalars(document_query):
        for index, term in enumerate(document.terms or []):
            if audience != "all" and term["calendar"] not in ("both", audience):
                continue
            records.append({"id": uuid5(document.id, f"term-{index}"), "title": f'{document.title} — {term["description"]}', "due_date": date.fromisoformat(term["due_date"]), "company_id": document.company_id, "document_id": document.id, "status": "planowany", "notes": term["description"], "deadline_types": []})
    for service in db.scalars(service_query):
        appointments = service.appointments
        if include_unscheduled:
            by_kind = {item["kind"]: item for item in appointments}
            appointments = [by_kind.get(kind, {"kind": kind}) for kind in service.deadline_types]
        for appointment in appointments:
            if appointment.get("due_date") or include_unscheduled:
                records.append({"id": uuid5(service.id, appointment["kind"]), "title": f'{service.name} — {appointment["kind"]}', "due_date": date.fromisoformat(appointment["due_date"]) if appointment.get("due_date") else None, "scheduled_time": appointment.get("scheduled_time"), "cost": appointment.get("cost"), "status": "wykonany" if appointment.get("completed") else "planowany", "notes": None, "company_id": service.company_id, "document_id": None, "service_id": service.template_id, "client_service_id": service.id, "deadline_types": [appointment["kind"]]})
    settings = {item.name_key: item for item in db.scalars(select(DeadlineType))}
    visible = []
    for record in records:
        kinds = record.get("deadline_types") or []
        matching = [settings.get(deadline_type_key(name)) for name in kinds]
        # A shared appointment is shown only if all its kinds permit this audience.
        if audience != "all" and any(item and not getattr(item, audience + "_calendar") for item in matching):
            continue
        record["address"] = " · ".join(dict.fromkeys(item.address for item in matching if item and item.address)) or None
        visible.append(record)
    return sorted(visible, key=lambda item: (item["due_date"] or date.max, item.get("scheduled_time") or "", item["title"]))


@app.post("/api/deadlines")
def add_deadline(data: DeadlineInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    if data.company_id and not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    if data.document_id:
        raise HTTPException(400, "Terminy dokumentów są dodawane automatycznie")
    if data.service_id:
        service = db.get(Service, data.service_id)
        if not service or service.deleted_at:
            raise HTTPException(404, "Nie znaleziono usługi")
        if any(value not in service.deadline_types for value in data.deadline_types):
            raise HTTPException(400, "Wybrany rodzaj terminu nie należy do tej usługi")
    elif data.deadline_types:
        raise HTTPException(400, "Wybierz usługę dla rodzajów terminu")
    if len(set(data.deadline_types)) != len(data.deadline_types):
        raise HTTPException(400, "Rodzaje terminów nie mogą się powtarzać")
    record = Deadline(**data.model_dump())
    db.add(record)
    db.commit()
    return {"id": record.id}


@app.post("/api/dashboard/today-summary")
def today_summary(response: Response, _: User = Depends(current_user), db: Session = Depends(db_session)):
    response.headers["Cache-Control"] = "no-store"
    today = datetime.now(ZoneInfo("Europe/Warsaw")).date()
    events = get_deadlines(db, include_unscheduled=True, audience="operator")
    closed_documents = {item.id for item in db.scalars(select(Document)) if str(item.status).strip().lower() in daily_summary.CLOSED}
    events = [event for event in events if event.get("document_id") not in closed_documents]
    overview = daily_summary.build_overview(events, list(db.scalars(select(ClientService))), today)
    if overview["ai_configured"]:
        try:
            overview["text"] = daily_summary.generate(overview["stats"], overview["date"])
            overview["source"] = "ai"
        except ValueError as cause:
            overview["notice"] = str(cause)
    return overview


def whatsapp_reminder_parameters(company, event):
    return [company.name, event["title"], event["due_date"].strftime("%d.%m.%Y"),
            event.get("scheduled_time") or "do ustalenia", event.get("address") or "do ustalenia"]


def notification_preferences(db):
    settings = db.get(NotificationSettings, 1, populate_existing=True)
    return {"default_method": settings.default_method if settings else "whatsapp",
            "automatic": settings.automatic if settings else os.getenv("WHATSAPP_AUTO_REMINDERS", "false").lower() == "true"}


def provider_configuration(provider):
    return smsapi.configuration() if provider == "smsapi" else whatsapp.configuration()


def whatsapp_deliver(db, key, company, kind, title, parameters, provider="whatsapp"):
    # Persist a unique claim before contacting Meta, including across API workers.
    # Pending/unknown claims are not retried: a timeout can mean Meta accepted it.
    record = WhatsAppDelivery(key=key, company_id=company.id, kind=kind, title=title[:500], status="pending", provider=provider)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.get(WhatsAppDelivery, key)
    try:
        send = smsapi.send_message if provider == "smsapi" else whatsapp.send_template
        record.message_id = send(company.phone, kind, parameters)
        record.status = "accepted"
    except (whatsapp.WhatsAppError, smsapi.SmsApiError) as cause:
        record.status = "unconfirmed"
        record.error = str(cause)
    db.commit()
    return record


def whatsapp_run_reminders(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Warsaw"))
    if now.hour < 9:
        return
    tomorrow = now.date() + timedelta(days=1)
    with SessionLocal() as db:
        preferences = notification_preferences(db)
        if not preferences["automatic"] or not provider_configuration(preferences["default_method"])["ready"]:
            return
        ids = list(db.scalars(select(WhatsAppSubscription.company_id)))
        for company_id in ids:
            company = db.get(Company, company_id)
            if not company:
                continue
            for event in get_deadlines(db, company_id, audience="client"):
                closed_statuses = ("wykonany", "zakończony", "zakończona", "gotowy", "wydany", "anulowany", "anulowana", "done", "completed", "cancelled", "canceled")
                if event["due_date"] != tomorrow or str(event.get("status", "")).strip().lower() in closed_statuses:
                    continue
                document = db.get(Document, event["document_id"]) if event.get("document_id") else None
                if document and str(document.status).strip().lower() in closed_statuses:
                    continue
                # Recheck subscription so disabling it takes effect within a batch.
                if not db.get(WhatsAppSubscription, company_id, populate_existing=True):
                    break
                key = f'reminder:{company_id}:{event["id"]}:{tomorrow.isoformat()}'
                if db.get(WhatsAppDelivery, key):
                    continue
                preferences = notification_preferences(db)
                if not preferences["automatic"] or not provider_configuration(preferences["default_method"])["ready"]:
                    return
                whatsapp_deliver(db, key, company, "reminder", event["title"], whatsapp_reminder_parameters(company, event), preferences["default_method"])


async def whatsapp_loop(stop):
    while not stop.is_set():
        try:
            await asyncio.to_thread(whatsapp_run_reminders)
        except Exception:
            logging.getLogger(__name__).error("Notification worker failed; check configuration and database connectivity.")
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass


@app.get("/api/notifications/settings")
@app.get("/api/whatsapp/settings")
def whatsapp_settings(_: User = Depends(admin_user), db: Session = Depends(db_session)):
    preferences = notification_preferences(db)
    return {**whatsapp.configuration(), **preferences,
            "providers": {"whatsapp": whatsapp.configuration(), "smsapi": smsapi.configuration()},
            "subscribed_clients": list(db.scalars(select(WhatsAppSubscription.company_id))),
            "history": [{"id": item.key, "company_id": item.company_id, "title": item.title, "status": item.status,
                         "created_at": item.created_at, "error": item.error, "provider": item.provider} for item in db.scalars(select(WhatsAppDelivery).order_by(WhatsAppDelivery.created_at.desc()).limit(50))]}


class NotificationSettingsInput(BaseModel):
    default_method: Literal["whatsapp", "smsapi"]
    automatic: bool


@app.put("/api/notifications/settings")
def save_notification_settings(data: NotificationSettingsInput, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    settings = db.get(NotificationSettings, 1)
    if not settings:
        settings = NotificationSettings(id=1)
        db.add(settings)
    settings.default_method = data.default_method
    settings.automatic = data.automatic
    db.commit()
    return notification_preferences(db)


@app.put("/api/notifications/subscriptions/{company_id}")
@app.put("/api/whatsapp/subscriptions/{company_id}")
def whatsapp_subscribe(company_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Nie znaleziono klienta")
    try:
        whatsapp.normalize_phone(company.phone)
    except whatsapp.WhatsAppError as cause:
        raise HTTPException(400, str(cause)) from cause
    if not db.get(WhatsAppSubscription, company_id):
        db.add(WhatsAppSubscription(company_id=company_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {"enabled": True}


@app.delete("/api/notifications/subscriptions/{company_id}")
@app.delete("/api/whatsapp/subscriptions/{company_id}")
def whatsapp_unsubscribe(company_id: UUID, _: User = Depends(admin_user), db: Session = Depends(db_session)):
    item = db.get(WhatsAppSubscription, company_id)
    if item:
        db.delete(item)
        db.commit()
    return {"enabled": False}


class WhatsAppLinkInput(BaseModel):
    request_id: UUID


@app.post("/api/whatsapp/services/{service_id}/link")
def whatsapp_send_link(service_id: UUID, data: WhatsAppLinkInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    return send_notification_link(service_id, data, user, db, "whatsapp")


@app.post("/api/notifications/services/{service_id}/link")
def notification_send_link(service_id: UUID, data: WhatsAppLinkInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    return send_notification_link(service_id, data, user, db, notification_preferences(db)["default_method"])


def send_notification_link(service_id, data, user, db, provider):
    if not provider_configuration(provider)["ready"]:
        raise HTTPException(400, "Najpierw skonfiguruj wybraną metodę wysyłki w backend/.env.")
    service = db.get(ClientService, service_id)
    if not service:
        raise HTTPException(404, "Nie znaleziono usługi")
    company = db.get(Company, service.company_id)
    try:
        whatsapp.normalize_phone(company.phone)
    except whatsapp.WhatsAppError as cause:
        raise HTTPException(400, str(cause)) from cause
    link = get_public_link(service_id, user, db)
    if not link["token"]:
        raise HTTPException(400, "Najpierw utwórz aktywny link w Usługi → Link usługi.")
    url = os.environ["PUBLIC_APP_URL"].rstrip("/") + "/#/service/" + link["token"]
    record = whatsapp_deliver(db, f"link:{service_id}:{data.request_id}", company, "link", f"Link: {service.name}", [company.name, url], provider)
    return {"status": record.status, "error": record.error, "provider": record.provider}


@app.get("/api/emails")
def emails(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(EmailMessage).order_by(EmailMessage.received_at.desc()).limit(50)).all()


from . import inbox
import sys
inbox.register(sys.modules[__name__])
