"""Integration tests using an isolated SQLite database and a local HTTP server.

Run: python -m unittest discover -s backend/tests -v
"""
import json
from contextlib import closing
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temp.name) / "test.db"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.url = f"http://127.0.0.1:{cls.port}/api"
        cls.environment = {**os.environ, "DATABASE_URL": f"sqlite:///{cls.database.as_posix()}", "APP_SECRET": "isolated-test-secret-not-production"}
        cls.start_server()
        status, result, _ = cls.call("POST", "/auth/login", {"email": "admin@tms.local", "password": "Admin123!"}, auth=False)
        assert status == 200, result
        cls.token = result["access_token"]

    @classmethod
    def start_server(cls):
        cls.process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(cls.port)], cwd=Path(__file__).resolve().parents[1], env=cls.environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError("Test API exited before startup")
            try:
                with urlopen(cls.url + "/health", timeout=.5) as response:
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(.1)
        cls.process.terminate()
        cls.process.wait(timeout=10)
        raise RuntimeError("Test API startup timed out")

    @classmethod
    def stop_server(cls):
        if os.name == "nt":
            # Windows virtualenv launchers may create a child interpreter.
            subprocess.run(["taskkill", "/PID", str(cls.process.pid), "/T", "/F"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            cls.process.terminate()
        cls.process.wait(timeout=10)

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        cls.temp.cleanup()

    @classmethod
    def call(cls, method, path, data=None, auth=True, content_type="application/json", extra_headers=None):
        headers = {"Content-Type": content_type}
        headers.update(extra_headers or {})
        if auth:
            headers["Authorization"] = f"Bearer {cls.token}"
        body = json.dumps(data).encode() if data is not None and not isinstance(data, bytes) else data
        try:
            response = urlopen(Request(cls.url + path, data=body, headers=headers, method=method), timeout=15)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            if "application/json" in response.headers.get("Content-Type", ""):
                body = json.loads(body)
            return response.status, body, response.headers

    def company(self):
        status, result, _ = self.call("POST", "/companies", {"kind": "firma", "name": "Testowa firma", "pesel": "12345678901"})
        self.assertEqual(status, 200, result)
        return result["id"]

    def document(self, due_date=None):
        company = self.company()
        status, result, _ = self.call("POST", "/documents", {"company_id": company, "title": "Umowa testowa", "due_date": due_date})
        self.assertEqual(status, 200, result)
        return result["id"], company

    def upload(self, document, files, auth=True):
        boundary = "test-" + uuid4().hex
        body = b""
        for name, content in files:
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        return self.call("POST", f"/documents/{document}/files", body, auth=auth, content_type=f"multipart/form-data; boundary={boundary}")

    def test_edit_company_preserves_and_updates_encrypted_pesel(self):
        company = self.company()
        def encrypted():
            with closing(sqlite3.connect(self.database)) as db:
                return db.execute("SELECT pesel_encrypted FROM companies WHERE id = ?", (company.replace("-", ""),)).fetchone()[0]
        original = encrypted()
        status, result, _ = self.call("PUT", f"/companies/{company}", {"kind": "firma", "name": "Nowa nazwa", "phone": "123456789"})
        self.assertEqual(status, 200)
        self.assertEqual(result["name"], "Nowa nazwa")
        self.assertEqual(result["phone"], "123456789")
        self.assertNotIn("pesel", result)
        self.assertEqual(encrypted(), original)
        status, details, headers = self.call("GET", f"/companies/{company}")
        self.assertEqual(status, 200)
        self.assertEqual(details["pesel"], "12345678901")
        self.assertEqual(headers["Cache-Control"], "no-store")
        status, _, _ = self.call("PUT", f"/companies/{company}", {"kind": "firma", "name": "Nowa nazwa", "pesel": "10987654321"})
        self.assertEqual(status, 200)
        self.assertNotEqual(encrypted(), original)
        self.assertNotIn("10987654321", encrypted())
        self.assertEqual(self.call("GET", f"/companies/{company}")[1]["pesel"], "10987654321")
        self.assertEqual(self.call("GET", f"/companies/{company}", auth=False)[0], 403)
        self.assertEqual(self.call("GET", f"/companies/{uuid4()}")[0], 404)
        _, companies, _ = self.call("GET", "/companies")
        self.assertTrue(all("pesel" not in item and "pesel_encrypted" not in item for item in companies))
        self.assertEqual(self.call("PUT", f"/companies/{uuid4()}", {"kind": "firma", "name": "Brak"})[0], 404)

    def test_company_without_pesel_can_be_opened_for_editing(self):
        status, company, _ = self.call("POST", "/companies", {"kind": "firma", "name": "Bez PESEL"})
        self.assertEqual(status, 200)
        status, details, _ = self.call("GET", f"/companies/{company['id']}")
        self.assertEqual(status, 200)
        self.assertIsNone(details["pesel"])
        self.assertIsNone(details["contact_type"])
        self.assertIsNone(details["birth_date"])
        self.assertIsNone(details["passport_number"])

    def test_client_birth_date_and_passport_round_trip(self):
        data = {"kind": "osoba", "name": "Klient testowy", "birth_date": "1990-05-12", "passport_number": "AB 1234567"}
        status, client, _ = self.call("POST", "/companies", data)
        self.assertEqual(status, 200, client)
        self.assertEqual(client["birth_date"], data["birth_date"])
        self.assertNotIn("passport_number", client)
        path = f"/companies/{client['id']}"
        _, details, _ = self.call("GET", path)
        self.assertEqual(details["birth_date"], data["birth_date"])
        self.assertEqual(details["passport_number"], data["passport_number"])
        with closing(sqlite3.connect(self.database)) as db:
            encrypted = db.execute("SELECT passport_number_encrypted FROM companies WHERE id = ?", (client["id"].replace("-", ""),)).fetchone()[0]
        self.assertNotIn(data["passport_number"], encrypted)
        data.update(birth_date="1991-06-13", passport_number="CD 7654321")
        self.assertEqual(self.call("PUT", path, data)[0], 200)
        self.assertEqual(self.call("GET", path)[1]["passport_number"], "CD 7654321")
        self.assertEqual(self.call("GET", path)[1]["birth_date"], "1991-06-13")
        del data["passport_number"]
        self.assertEqual(self.call("PUT", path, data)[0], 200)
        self.assertEqual(self.call("GET", path)[1]["passport_number"], "CD 7654321")
        data.update(birth_date=None, passport_number=None)
        self.assertEqual(self.call("PUT", path, data)[0], 200)
        _, details, _ = self.call("GET", path)
        self.assertIsNone(details["birth_date"])
        self.assertIsNone(details["passport_number"])
        for changes in ({"birth_date": "2999-01-01"}, {"birth_date": "1990-02-30"}, {"passport_number": "A" * 101}):
            self.assertEqual(self.call("POST", "/companies", {**data, **changes})[0], 422)

    def test_client_employer_create_edit_and_clear(self):
        fields = {"employer_name": "Pracodawca testowy", "employer_email": "biuro@example.com", "employer_phone": "+48 123 456 789"}
        data = {"kind": "osoba", "name": "Klient testowy", **fields}
        status, client, _ = self.call("POST", "/companies", data)
        self.assertEqual(status, 200, client)
        path = f"/companies/{client['id']}"
        for key, value in fields.items():
            self.assertEqual(client[key], value)
            self.assertEqual(self.call("GET", path)[1][key], value)
        changed = {"employer_name": "Nowy pracodawca", "employer_email": "kontakt@example.com", "employer_phone": "+48 987 654 321"}
        self.assertEqual(self.call("PUT", path, {**data, **changed})[0], 200)
        _, clients, _ = self.call("GET", "/companies")
        stored = next(item for item in clients if item["id"] == client["id"])
        for key, value in changed.items():
            self.assertEqual(stored[key], value)
        self.assertEqual(self.call("PUT", path, {**data, **dict.fromkeys(fields, "")})[0], 200)
        _, cleared, _ = self.call("GET", path)
        self.assertTrue(all(cleared[key] == "" for key in fields))

    def test_company_contact_type_create_edit_and_clear(self):
        for contact_type in ("email", "phone", "whatsapp", "viber", "telegram"):
            with self.subTest(contact_type=contact_type):
                data = {"kind": "firma", "name": "Kontakt testowy", "contact_type": contact_type}
                status, company, _ = self.call("POST", "/companies", data)
                self.assertEqual(status, 200)
                self.assertEqual(company["contact_type"], contact_type)
                path = f"/companies/{company['id']}"
                self.assertEqual(self.call("GET", path)[1]["contact_type"], contact_type)
                data["contact_type"] = "phone" if contact_type != "phone" else "email"
                self.assertEqual(self.call("PUT", path, data)[0], 200)
                _, companies, _ = self.call("GET", "/companies")
                stored = next(item for item in companies if item["id"] == company["id"])
                self.assertEqual(stored["contact_type"], data["contact_type"])
                data["contact_type"] = None
                self.assertEqual(self.call("PUT", path, data)[0], 200)
                self.assertIsNone(self.call("GET", path)[1]["contact_type"])
        self.assertEqual(self.call("POST", "/companies", {"kind": "firma", "name": "Błędny kontakt", "contact_type": "unknown"})[0], 422)

    def test_client_residential_address_create_edit_and_clear(self):
        data = {"kind": "osoba", "name": "Klient testowy", "residential_address": "ul. Leśna 12/4, 00-001 Warszawa, Polska"}
        status, client, _ = self.call("POST", "/companies", data)
        self.assertEqual(status, 200)
        self.assertEqual(client["residential_address"], data["residential_address"])
        path = f"/companies/{client['id']}"
        self.assertEqual(self.call("GET", path)[1]["residential_address"], data["residential_address"])
        data["residential_address"] = "ul. Długa 8, 31-001 Kraków"
        self.assertEqual(self.call("PUT", path, data)[0], 200)
        _, clients, _ = self.call("GET", "/companies")
        self.assertEqual(next(item for item in clients if item["id"] == client["id"])["residential_address"], data["residential_address"])
        data["residential_address"] = ""
        self.assertEqual(self.call("PUT", path, data)[0], 200)
        self.assertEqual(self.call("GET", path)[1]["residential_address"], "")

    def test_document_deadline_and_optional_date(self):
        dated, company = self.document("2026-10-15")
        undated, _ = self.document()
        status, deadlines, _ = self.call("GET", "/deadlines")
        self.assertEqual(status, 200)
        linked = [event for event in deadlines if event["document_id"] == dated]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["due_date"], "2026-10-15")
        self.assertEqual(linked[0]["company_id"], company)
        self.assertFalse(any(event["document_id"] == undated for event in deadlines))
        self.assertEqual(self.call("POST", "/deadlines", {"title": "Bez firmy", "due_date": "2026-10-16", "company_id": None})[0], 200)
        self.assertEqual(self.call("POST", "/documents", {"title": "Brak firmy", "company_id": str(uuid4())})[0], 404)

    def test_document_types_defaults_custom_and_document_assignment(self):
        status, types, _ = self.call("GET", "/document-types")
        self.assertEqual(status, 200)
        defaults = {"Paszport", "Karta pobytu", "Umowa najmu", "Prawo jazdy", "PESEL", "Akt urodzenia", "Akt małżeństwa", "Ubezpieczenie", "Meldunek", "Zdjęcie"}
        self.assertTrue(defaults.issubset({item["name"] for item in types}))
        status, custom, _ = self.call("POST", "/document-types", {"name": "  Zaświadczenie   testowe  "})
        self.assertEqual(status, 200)
        self.assertEqual(custom["name"], "Zaświadczenie testowe")
        self.assertEqual(self.call("POST", "/document-types", {"name": "zaświadczenie TESTOWE"})[0], 409)
        for name in ("", "   ", "A" * 101):
            self.assertEqual(self.call("POST", "/document-types", {"name": name})[0], 422)
        data = {"company_id": self.company(), "title": "Zaświadczenie klienta", "document_type_id": custom["id"], "due_date": "2027-01-01"}
        status, document, _ = self.call("POST", "/documents", data)
        self.assertEqual(status, 200, document)
        _, documents, _ = self.call("GET", "/documents")
        self.assertEqual(next(item for item in documents if item["id"] == document["id"])["document_type_id"], custom["id"])
        self.assertEqual(self.call("POST", "/documents", {**data, "document_type_id": str(uuid4())})[0], 404)
        _, deadlines, _ = self.call("GET", "/deadlines")
        self.assertEqual(len([item for item in deadlines if item["document_id"] == document["id"]]), 1)
        self.assertEqual(self.call("GET", "/document-types", auth=False)[0], 403)
        self.assertEqual(self.call("POST", "/document-types", {"name": "Test"}, auth=False)[0], 403)

    def test_services_create_edit_price_and_types(self):
        status, services, _ = self.call("GET", "/services")
        self.assertEqual(status, 200)
        self.assertEqual(len([service for service in services if service["name"] == "KOD95"]), 1)
        data = {"name": "Szkolenie testowe", "price": "1234.56", "description": "Opis usługi", "deadline_types": ["Szkolenie", "Egzamin"]}
        status, service, _ = self.call("POST", "/services", data)
        self.assertEqual(status, 200, service)
        self.assertEqual(service["price"], "1234.56")
        self.assertEqual(service["deadline_types"], data["deadline_types"])
        data.update(price="0.00", description="Nowy opis", deadline_types=["Badania", "Odbiór"])
        status, updated, _ = self.call("PUT", f"/services/{service['id']}", data)
        self.assertEqual(status, 200)
        self.assertEqual(updated["price"], "0.00")
        _, services, _ = self.call("GET", "/services")
        stored = next(item for item in services if item["id"] == service["id"])
        self.assertEqual(stored["description"], "Nowy opis")
        self.assertEqual(stored["deadline_types"], ["Badania", "Odbiór"])
        self.assertEqual(self.call("GET", "/services", auth=False)[0], 403)
        for changes in ({"price": "-1"}, {"price": "1.234"}, {"name": " "}, {"deadline_types": ["Egzamin", "egzamin"]}, {"deadline_types": [""]}):
            self.assertEqual(self.call("POST", "/services", {**data, **changes})[0], 422)
        self.assertEqual(self.call("PUT", f"/services/{uuid4()}", data)[0], 404)

    def test_service_multiple_deadline_types(self):
        _, service, _ = self.call("POST", "/services", {"name": "Usługa do kalendarza", "deadline_types": ["Badania", "Szkolenie", "Egzamin"]})
        data = {"title": "Wizyta klienta", "due_date": "2026-12-01", "service_id": service["id"], "deadline_types": ["Badania", "Szkolenie"]}
        status, deadline, _ = self.call("POST", "/deadlines", data)
        self.assertEqual(status, 200, deadline)
        _, deadlines, _ = self.call("GET", "/deadlines")
        stored = next(item for item in deadlines if item["id"] == deadline["id"])
        self.assertEqual(stored["service_id"], service["id"])
        self.assertEqual(stored["deadline_types"], ["Badania", "Szkolenie"])
        for changes in ({"deadline_types": ["Obcy rodzaj"]}, {"service_id": None}, {"deadline_types": ["Badania", "Badania"]}):
            self.assertEqual(self.call("POST", "/deadlines", {**data, **changes})[0], 400)
        self.assertEqual(self.call("POST", "/deadlines", {**data, "service_id": str(uuid4())})[0], 404)
        # Updating the offer must not rewrite previously scheduled appointment types.
        self.call("PUT", f"/services/{service['id']}", {"name": "Usługa do kalendarza", "deadline_types": ["Nowy rodzaj"]})
        _, deadlines, _ = self.call("GET", "/deadlines")
        self.assertEqual(next(item for item in deadlines if item["id"] == deadline["id"])["deadline_types"], ["Badania", "Szkolenie"])

    def test_client_service_copies_template_and_keeps_snapshot(self):
        company_id = self.company()
        template_data = {"name": "Szablon KOD95 test", "price": "2500.50", "description": "Opis z szablonu", "deadline_types": ["Badania", "Egzamin"]}
        status, template, _ = self.call("POST", "/service-types", template_data)
        self.assertEqual(status, 200)
        data = {"template_id": template["id"], "company_id": company_id}
        status, service, _ = self.call("POST", "/client-services", data)
        self.assertEqual(status, 200, service)
        self.assertEqual(service["company_id"], company_id)
        self.assertEqual(service["template_id"], template["id"])
        self.assertNotEqual(service["id"], template["id"])
        for key, value in template_data.items():
            self.assertEqual(service[key], value)
        self.assertEqual(self.call("PUT", f"/service-types/{template['id']}", {**template_data, "name": "Zmieniony szablon", "price": "3000.00", "description": "Nowy opis", "deadline_types": ["Inny termin"]})[0], 200)
        _, services, _ = self.call("GET", "/client-services")
        stored = next(item for item in services if item["id"] == service["id"])
        for key, value in template_data.items():
            self.assertEqual(stored[key], value)
        _, templates, _ = self.call("GET", "/service-types")
        self.assertFalse(any(item["id"] == service["id"] for item in templates))
        self.assertEqual(self.call("POST", "/client-services", {**data, "company_id": str(uuid4())})[0], 404)
        self.assertEqual(self.call("POST", "/client-services", {**data, "template_id": str(uuid4())})[0], 404)
        self.assertEqual(self.call("POST", "/client-services", {"template_id": template["id"]})[0], 422)
        self.assertEqual(self.call("POST", "/client-services", data, auth=False)[0], 403)
        self.assertEqual(self.call("GET", "/client-services", auth=False)[0], 403)

    def test_client_service_with_unset_template_price(self):
        _, template, _ = self.call("POST", "/service-types", {"name": "Bez ceny"})
        status, service, _ = self.call("POST", "/client-services", {"template_id": template["id"], "company_id": self.company()})
        self.assertEqual(status, 200)
        self.assertIsNone(service["price"])
        self.assertEqual(service["deadline_types"], [])
        self.assertEqual(service["progress"], 0)

    def test_public_service_scoping(self):
        document, company = self.document("2027-02-01")
        foreign_document, foreign_company = self.document("2027-02-02")
        _, files, _ = self.upload(document, [("client.txt", b"own content")])
        _, foreign_files, _ = self.upload(foreign_document, [("foreign.txt", b"private")])
        _, template, _ = self.call("POST", "/service-types", {"name": "Usługa publiczna", "deadline_types": ["Badania"]})
        _, own_service, _ = self.call("POST", "/client-services", {"company_id": company, "template_id": template["id"], "appointments": [{"kind": "Badania", "due_date": "2027-03-01"}]})
        self.call("POST", "/client-services", {"company_id": company, "template_id": template["id"], "appointments": [{"kind": "Badania", "due_date": "2027-04-01"}]})
        self.call("POST", "/client-services", {"company_id": foreign_company, "template_id": template["id"]})
        self.call("POST", "/client-services", {"company_id": company, "template_id": template["id"]})
        self.call("POST", "/deadlines", {"company_id": company, "title": "Własny termin", "due_date": "2027-01-01"})
        self.call("POST", "/deadlines", {"company_id": foreign_company, "title": "Obcy termin", "due_date": "2027-01-01"})
        status, link, _ = self.call("POST", f"/client-services/{own_service['id']}/public-link")
        self.assertEqual(status, 200)
        headers = {"X-Client-Token": link["token"]}
        status, body, response_headers = self.call("GET", "/public/service", auth=False, extra_headers=headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(response_headers["Cache-Control"], "no-store")
        self.assertIn("noindex", response_headers["X-Robots-Tag"])
        self.assertEqual(body["client"]["id"], company)
        self.assertEqual(set(body["client"]), {"id", "name"})
        self.assertNotIn("documents", body)
        self.assertNotIn("services", body)
        self.assertTrue(all(item["company_id"] == company for item in body["deadlines"]))
        self.assertEqual(len(body["deadlines"]), 5)
        self.assertEqual(sum(item["due_date"] is None for item in body["deadlines"]), 1)
        self.assertEqual(body["deadlines"][0]["title"], "Własny termin")
        self.assertIsNone(body["deadlines"][-1]["due_date"])
        self.assertTrue(any(item["document_id"] == document for item in body["deadlines"]))
        status, content, _ = self.call("GET", f"/public/files/{files[0]['id']}", auth=False, extra_headers=headers)
        self.assertEqual(status, 404)
        self.assertEqual(self.call("GET", f"/public/files/{foreign_files[0]['id']}", auth=False, extra_headers=headers)[0], 404)
        self.assertEqual(self.call("GET", f"/public/files/{files[0]['id']}", auth=False)[0], 404)
        self.assertEqual(self.call("GET", "/companies", auth=False, extra_headers=headers)[0], 403)

    def test_public_link_rotation_revocation_expiration(self):
        company = self.company()
        _, template, _ = self.call("POST", "/service-types", {"name": "Link testowy"})
        _, own_service, _ = self.call("POST", "/client-services", {"company_id": company, "template_id": template["id"]})
        path = f"/client-services/{own_service['id']}/public-link"
        self.assertIsNone(self.call("GET", path)[1]["token"])
        for method in ("GET", "POST", "DELETE"):
            self.assertEqual(self.call(method, path, auth=False)[0], 403)
        _, first, _ = self.call("POST", path)
        self.assertEqual(self.call("GET", path)[1]["token"], first["token"])
        with closing(sqlite3.connect(self.database)) as db:
            stored = db.execute("SELECT token_hash, token_encrypted FROM service_public_links WHERE service_id = ?", (own_service["id"].replace("-", ""),)).fetchone()
        self.assertNotIn(first["token"], stored)
        _, second, _ = self.call("POST", path)
        self.assertNotEqual(first["token"], second["token"])
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": first["token"]})[0], 404)
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": second["token"]})[0], 200)
        self.assertEqual(self.call("DELETE", path)[0], 200)
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": second["token"]})[0], 404)
        _, third, _ = self.call("POST", path)
        with closing(sqlite3.connect(self.database)) as db:
            db.execute("UPDATE service_public_links SET expires_at = '2000-01-01 00:00:00' WHERE service_id = ?", (own_service["id"].replace("-", ""),))
            db.commit()
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": third["token"]})[0], 404)
        self.assertIsNone(self.call("GET", path)[1]["token"])
        self.assertEqual(self.call("GET", "/public/service", auth=False)[0], 404)
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": "invalid"})[0], 404)
        self.assertEqual(self.call("POST", f"/client-services/{uuid4()}/public-link")[0], 404)
        _, fourth, _ = self.call("POST", path)
        update = {"company_id": self.company(), "name": own_service["name"]}
        self.assertEqual(self.call("PUT", f"/client-services/{own_service['id']}", update)[0], 200)
        self.assertEqual(self.call("GET", "/public/service", auth=False, extra_headers={"X-Client-Token": fourth["token"]})[0], 404)
        self.assertIsNone(self.call("GET", path)[1]["token"])
        self.assertEqual(self.call("GET", "/public/client", auth=False)[0], 404)

    def test_service_completed_terms_persist_and_can_be_reopened(self):
        kinds = [f"Termin {number}" for number in range(1, 8)]
        _, template, _ = self.call("POST", "/service-types", {"name": "Siedem terminów", "deadline_types": kinds})
        company_id = self.company()
        _, service, _ = self.call("POST", "/client-services", {"template_id": template["id"], "company_id": company_id})
        data = {"company_id": company_id, "name": service["name"], "deadline_types": kinds, "appointments": [{"kind": kind, "due_date": "2027-01-01", "completed": index < 3} for index, kind in enumerate(kinds)]}
        status, updated, _ = self.call("PUT", f"/client-services/{service['id']}", data)
        self.assertEqual(status, 200)
        self.assertEqual(sum(item["completed"] for item in updated["appointments"]), 3)
        _, stored, _ = self.call("GET", "/client-services")
        self.assertEqual(sum(item["completed"] for item in next(item for item in stored if item["id"] == service["id"])["appointments"]), 3)
        _, events, _ = self.call("GET", "/deadlines")
        linked = [item for item in events if item.get("client_service_id") == service["id"]]
        self.assertEqual(len(linked), 7)
        self.assertEqual(sum(item["status"] == "wykonany" for item in linked), 3)
        data["appointments"][0]["completed"] = False
        _, updated, _ = self.call("PUT", f"/client-services/{service['id']}", data)
        self.assertEqual(sum(item["completed"] for item in updated["appointments"]), 2)

    def test_client_service_progress_persistence_and_limits(self):
        _, template, _ = self.call("POST", "/service-types", {"name": "Postęp testowy"})
        company_id = self.company()
        _, service, _ = self.call("POST", "/client-services", {"template_id": template["id"], "company_id": company_id})
        path = f"/client-services/{service['id']}"
        data = {"company_id": company_id, "name": service["name"]}
        for progress in (25, 100, 0, 60):
            status, updated, _ = self.call("PUT", path, {**data, "progress": progress})
            self.assertEqual(status, 200)
            self.assertEqual(updated["progress"], progress)
            _, services, _ = self.call("GET", "/client-services")
            self.assertEqual(next(item for item in services if item["id"] == service["id"])["progress"], progress)
        self.assertEqual(self.call("PUT", path, data)[1]["progress"], 60)
        for invalid in (-1, 101, 12.5, None):
            self.assertEqual(self.call("PUT", path, {**data, "progress": invalid})[0], 422)

    def test_service_appointment_date_time_cost_and_calendar(self):
        _, template, _ = self.call("POST", "/service-types", {"name": "Plan usługi", "deadline_types": ["Badania", "Egzamin"]})
        appointments = [{"kind": "Badania", "due_date": "2027-03-15", "scheduled_time": "09:30", "cost": "150.25"}, {"kind": "Egzamin", "due_date": None, "cost": "0.00"}]
        data = {"template_id": template["id"], "company_id": self.company(), "appointments": appointments}
        status, service, _ = self.call("POST", "/client-services", data)
        self.assertEqual(status, 200, service)
        self.assertEqual(service["appointments"][0]["cost"], "150.25")
        _, events, _ = self.call("GET", "/deadlines")
        linked = [item for item in events if item.get("client_service_id") == service["id"]]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["scheduled_time"], "09:30")
        self.assertEqual(linked[0]["due_date"], "2027-03-15")
        original_id = linked[0]["id"]
        update = {"company_id": data["company_id"], "name": service["name"], "deadline_types": service["deadline_types"], "appointments": [{**appointments[0], "due_date": "2027-03-16", "scheduled_time": "10:45"}]}
        for _ in range(2):
            self.assertEqual(self.call("PUT", f"/client-services/{service['id']}", update)[0], 200)
        _, events, _ = self.call("GET", "/deadlines")
        linked = [item for item in events if item.get("client_service_id") == service["id"]]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["id"], original_id)
        self.assertEqual(linked[0]["due_date"], "2027-03-16")
        self.assertEqual(linked[0]["scheduled_time"], "10:45")
        for value in ("9:00–12:00", "do ustalenia", "09:30:00", None):
            update["appointments"][0]["scheduled_time"] = value
            status, edited, _ = self.call("PUT", f"/client-services/{service['id']}", update)
            self.assertEqual(status, 200)
            self.assertEqual(edited["appointments"][0]["scheduled_time"], value)
            _, events, _ = self.call("GET", "/deadlines")
            self.assertEqual(next(item for item in events if item.get("client_service_id") == service["id"])["scheduled_time"], value)
        for appointment in ({**appointments[0], "due_date": None}, {**appointments[0], "cost": "-1"}, {**appointments[0], "scheduled_time": "x" * 101}):
            self.assertEqual(self.call("POST", "/client-services", {**data, "appointments": [appointment]})[0], 422)
        self.assertEqual(self.call("POST", "/client-services", {**data, "appointments": [{"kind": "Obcy"}]})[0], 400)
        self.assertEqual(self.call("POST", "/client-services", {**data, "appointments": [appointments[0], appointments[0]]})[0], 400)
        self.assertEqual(self.call("PUT", f"/client-services/{service['id']}", {**update, "appointments": []})[0], 200)
        _, events, _ = self.call("GET", "/deadlines")
        self.assertFalse(any(item.get("client_service_id") == service["id"] for item in events))

    def test_client_service_edit_preserves_template_and_other_services(self):
        original = {"name": "Szablon edycji", "price": "100.00", "description": "Opis szablonu", "deadline_types": ["Egzamin"]}
        _, template, _ = self.call("POST", "/service-types", original)
        data = {"template_id": template["id"], "company_id": self.company()}
        _, service, _ = self.call("POST", "/client-services", data)
        _, other, _ = self.call("POST", "/client-services", data)
        path = f"/client-services/{service['id']}"
        changes = {"company_id": self.company(), "name": "Usługa indywidualna", "price": "250.50", "description": "Uzgodniony zakres", "deadline_types": ["Badania", "Szkolenie"]}
        status, updated, _ = self.call("PUT", path, changes)
        self.assertEqual(status, 200, updated)
        for key, value in changes.items():
            self.assertEqual(updated[key], value)
        self.assertEqual(updated["template_id"], template["id"])
        self.assertEqual(updated["created_at"], service["created_at"])
        _, stored, _ = self.call("GET", "/client-services")
        self.assertEqual(next(item for item in stored if item["id"] == service["id"])["price"], "250.50")
        self.assertEqual(next(item for item in stored if item["id"] == other["id"])["price"], "100.00")
        _, templates, _ = self.call("GET", "/service-types")
        self.assertEqual(next(item for item in templates if item["id"] == template["id"])["price"], "100.00")
        self.assertEqual(self.call("PUT", path, {**changes, "company_id": str(uuid4())})[0], 404)
        self.assertEqual(self.call("PUT", f"/client-services/{uuid4()}", changes)[0], 404)
        self.assertEqual(self.call("PUT", path, changes, auth=False)[0], 403)
        for invalid in ({"price": "-1"}, {"price": "1.234"}, {"name": " "}, {"deadline_types": ["Egzamin", "egzamin"]}):
            self.assertEqual(self.call("PUT", path, {**changes, **invalid})[0], 422)
        status, cleared, _ = self.call("PUT", path, {**changes, "price": None, "description": "", "deadline_types": []})
        self.assertEqual(status, 200)
        self.assertIsNone(cleared["price"])
        self.assertEqual(cleared["deadline_types"], [])

    def test_files_round_trip_and_metadata(self):
        document, company = self.document()
        content = b"%PDF-1.7\nTest\x00\xff"
        status, files, _ = self.upload(document, [("umowa.pdf", content), ("../notatka.txt", b"Note")])
        self.assertEqual(status, 200, files)
        self.assertEqual(len(files), 2)
        self.assertEqual(files[1]["name"], "notatka.txt")
        status, downloaded, headers = self.call("GET", f"/documents/{document}/files/{files[0]['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, content)
        self.assertIn("attachment", headers["Content-Disposition"])
        _, documents, _ = self.call("GET", "/documents")
        stored = next(item for item in documents if item["id"] == document)
        self.assertEqual(stored["company_id"], company)
        self.assertEqual(len(stored["files"]), 2)
        self.assertEqual(stored["files"][0]["size"], len(content))
        self.assertNotIn("content", stored["files"][0])
        self.assertEqual(self.call("GET", f"/documents/{uuid4()}/files/{files[0]['id']}")[0], 404)
        self.assertEqual(self.call("GET", f"/documents/{document}/files/{files[0]['id']}", auth=False)[0], 403)

    def test_upload_limits_are_atomic(self):
        document, _ = self.document()
        self.assertEqual(self.upload(document, [("ok.txt", b"OK"), ("large.bin", b"x" * (20 * 1024 * 1024 + 1))])[0], 413)
        self.assertEqual(self.upload(document, [(f"{i}.txt", b"x") for i in range(11)])[0], 400)
        self.assertEqual(self.upload(document, [("test.txt", b"x")], auth=False)[0], 403)
        self.assertEqual(self.upload(str(uuid4()), [("test.txt", b"x")])[0], 404)
        _, documents, _ = self.call("GET", "/documents")
        self.assertEqual(next(item for item in documents if item["id"] == document)["files"], [])

    def test_existing_documents_backfilled_once(self):
        document, _ = self.document()
        with closing(sqlite3.connect(self.database)) as db:
            db.execute("UPDATE documents SET due_date = '2026-11-01' WHERE id = ?", (document.replace("-", ""),))
            db.commit()
        for _ in range(2):
            self.stop_server()
            self.start_server()
            _, deadlines, _ = self.call("GET", "/deadlines")
            linked = [event for event in deadlines if event["document_id"] == document]
            self.assertEqual(len(linked), 1)
            self.assertEqual(linked[0]["due_date"], "2026-11-01")
            _, services, _ = self.call("GET", "/services")
            self.assertEqual(len([item for item in services if item["name"] == "KOD95"]), 1)
            _, types, _ = self.call("GET", "/document-types")
            self.assertEqual(len([item for item in types if item["name"] == "Paszport"]), 1)


if __name__ == "__main__":
    unittest.main()
