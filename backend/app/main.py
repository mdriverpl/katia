from __future__ import annotations

import base64
import hashlib
import imaplib
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from email import message_from_bytes
from uuid import UUID, uuid4, uuid5
from urllib.parse import quote
from typing import Literal

import jwt
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Header
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, LargeBinary, Numeric, JSON, create_engine, select, text, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError

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


class DocumentType(Base):
    __tablename__ = "document_types"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)


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
    company: Mapped[Company] = relationship(back_populates="documents")


class Service(Base):
    __tablename__ = "services"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    deadline_types: Mapped[list[str]] = mapped_column(JSON, default=list)


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


class DocumentFileOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    size: int


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
    first_name: str | None = None
    last_name: str | None = None
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
    company_id: UUID
    document_type_id: UUID | None = None
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
    service_id: UUID | None = None
    deadline_types: list[str] = Field(default_factory=list, max_length=30)


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
    with engine.begin() as connection:
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
        if "document_type_id" not in document_columns:
            uuid_type = "UUID" if connection.dialect.name == "postgresql" else "CHAR(32)"
            connection.execute(text(f"ALTER TABLE documents ADD COLUMN document_type_id {uuid_type} REFERENCES document_types(id)"))
        deadline_columns = {column["name"] for column in inspect(connection).get_columns("deadlines")}
        if "service_id" not in deadline_columns:
            uuid_type = "UUID" if connection.dialect.name == "postgresql" else "CHAR(32)"
            connection.execute(text(f"ALTER TABLE deadlines ADD COLUMN service_id {uuid_type} REFERENCES services(id)"))
        if "deadline_types" not in deadline_columns:
            connection.execute(text("ALTER TABLE deadlines ADD COLUMN deadline_types JSON"))
        service_columns = {column["name"] for column in inspect(connection).get_columns("client_services")}
        if "appointments" not in service_columns:
            connection.execute(text("ALTER TABLE client_services ADD COLUMN appointments JSON NOT NULL DEFAULT '[]'"))
        if "progress" not in service_columns:
            connection.execute(text("ALTER TABLE client_services ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"))
    with SessionLocal() as db:
        for name in ("Paszport", "Karta pobytu", "Umowa najmu", "Prawo jazdy", "PESEL", "Akt urodzenia", "Akt małżeństwa", "Ubezpieczenie", "Meldunek", "Zdjęcie"):
            if not db.scalar(select(DocumentType).where(DocumentType.name_key == name.casefold())):
                db.add(DocumentType(name=name, name_key=name.casefold()))
        kod95_id = UUID("fcf9394e-d124-4ac5-9544-b8a41964a6eb")
        if not db.get(Service, kod95_id) and not db.scalar(select(Service).where(Service.name == "KOD95")):
            db.add(Service(id=kod95_id, name="KOD95", price=None, description=None, deadline_types=[]))
        # Include existing dated documents once, including records created before this feature.
        for document in db.scalars(select(Document).where(Document.due_date.is_not(None), ~select(Deadline.id).where(Deadline.document_id == Document.id).exists())):
            db.add(Deadline(title=document.title, due_date=document.due_date, company_id=document.company_id, document_id=document.id, status="planowany"))
        if not db.scalar(select(User).where(User.email == "admin@tms.local")):
            db.add(User(email="admin@tms.local", password_hash=password_hash("Admin123!")))
        db.commit()
    yield


app = FastAPI(title="TMS", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def public_privacy_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/public/") or request.url.path.endswith("/public-link"):
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
        "deadlines": get_deadlines(db, service.company_id, include_unscheduled=True),
    }


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


@app.get("/api/document-types", response_model=list[DocumentTypeOutput])
def document_types(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(DocumentType).order_by(DocumentType.name)).all()


@app.post("/api/document-types", response_model=DocumentTypeOutput)
def add_document_type(data: DocumentTypeInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    name = " ".join(data.name.split())
    record = DocumentType(name=name, name_key=name.casefold())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(409, "Taki rodzaj dokumentu już istnieje") from cause
    db.refresh(record)
    return record


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
    if data.document_type_id and not db.get(DocumentType, data.document_type_id):
        raise HTTPException(404, "Nie znaleziono rodzaju dokumentu")
    record = Document(**data.model_dump())
    db.add(record)
    db.flush()
    if record.due_date:
        db.add(Deadline(title=record.title, due_date=record.due_date, company_id=record.company_id, document_id=record.id, status="planowany"))
    db.commit()
    return {"id": record.id}


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
        attachments.append(DocumentFile(document_id=document_id, name=name, content=content, size=len(content)))
    db.add_all(attachments)
    db.commit()
    return attachments


@app.get("/api/documents/{document_id}/files/{file_id}")
def download_file(document_id: UUID, file_id: UUID, _: User = Depends(current_user), db: Session = Depends(db_session)):
    attachment = db.get(DocumentFile, file_id)
    if not attachment or attachment.document_id != document_id:
        raise HTTPException(404, "Nie znaleziono pliku")
    return Response(attachment.content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.name, safe='')}", "X-Content-Type-Options": "nosniff"})


@app.get("/api/services", response_model=list[ServiceOutput])
@app.get("/api/service-types", response_model=list[ServiceOutput])
def services(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(Service).order_by(Service.name)).all()


@app.post("/api/services", response_model=ServiceOutput)
@app.post("/api/service-types", response_model=ServiceOutput)
def add_service(data: ServiceInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@app.put("/api/services/{service_id}", response_model=ServiceOutput)
@app.put("/api/service-types/{service_id}", response_model=ServiceOutput)
def update_service(service_id: UUID, data: ServiceInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Nie znaleziono usługi")
    for key, value in data.model_dump().items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@app.get("/api/client-services", response_model=list[ClientServiceOutput])
def client_services(_: User = Depends(current_user), db: Session = Depends(db_session)):
    return db.scalars(select(ClientService).order_by(ClientService.created_at.desc(), ClientService.id)).all()


@app.post("/api/client-services", response_model=ClientServiceOutput)
def add_client_service(data: ClientServiceInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    template = db.get(Service, data.template_id)
    if not template:
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


def get_deadlines(db: Session, company_id: UUID | None = None, include_unscheduled: bool = False):
    deadline_query = select(Deadline)
    service_query = select(ClientService)
    if company_id is not None:
        deadline_query = deadline_query.where(Deadline.company_id == company_id)
        service_query = service_query.where(ClientService.company_id == company_id)
    records = [{column.name: getattr(item, column.name) for column in Deadline.__table__.columns} for item in db.scalars(deadline_query)]
    for service in db.scalars(service_query):
        appointments = service.appointments
        if include_unscheduled:
            by_kind = {item["kind"]: item for item in appointments}
            appointments = [by_kind.get(kind, {"kind": kind}) for kind in service.deadline_types]
        for appointment in appointments:
            if appointment.get("due_date") or include_unscheduled:
                records.append({"id": uuid5(service.id, appointment["kind"]), "title": f'{service.name} — {appointment["kind"]}', "due_date": date.fromisoformat(appointment["due_date"]) if appointment.get("due_date") else None, "scheduled_time": appointment.get("scheduled_time"), "cost": appointment.get("cost"), "status": "wykonany" if appointment.get("completed") else "planowany", "notes": None, "company_id": service.company_id, "document_id": None, "service_id": service.template_id, "client_service_id": service.id, "deadline_types": [appointment["kind"]]})
    return sorted(records, key=lambda item: (item["due_date"] or date.max, item.get("scheduled_time") or "", item["title"]))


@app.post("/api/deadlines")
def add_deadline(data: DeadlineInput, _: User = Depends(current_user), db: Session = Depends(db_session)):
    if data.company_id and not db.get(Company, data.company_id):
        raise HTTPException(404, "Nie znaleziono klienta")
    if data.document_id:
        raise HTTPException(400, "Terminy dokumentów są dodawane automatycznie")
    if data.service_id:
        service = db.get(Service, data.service_id)
        if not service:
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
