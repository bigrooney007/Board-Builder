# Iteration 51 — Global Document Design Standard (document_renderer + PDF endpoints + shared page API)
import base64
import io
import os
import sys
import zlib

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, "/app/backend")

backend_env = dotenv_values("/app/backend/.env")
for key, value in backend_env.items():
    os.environ.setdefault(key, value or "")

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")

RECRUIT_USER = "f75a06c6-8331-4269-8065-2532715406e0"
RECRUIT_EMAIL = "rooney+iter16-a-30fa5729@nonprofitboardbuilder.com"
RECRUIT_MATERIAL = "fcd4fddabaf349ce953e68460c4cb054"
REACT_USER = "b0f96ec0-f045-4c47-a81b-3badbdd1bda6"
REACT_EMAIL = "test_ui_batch2_6ca82f@example.com"
REACT_MATERIAL = "c32a70d1-42ec-44e1-b439-9f6a061a63ae"
SHARE_TOKEN = "1a355163f37b4646b898e8b816a7d303"
ARTIFACTS = ["Title:", "Content:", "Sections:", "Version 1"]


def pdf_text(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages), len(reader.pages)


@pytest.fixture(scope="session")
def db():
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    loop = asyncio.new_event_loop()
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=loop)
    database = client[os.environ["DB_NAME"]]

    class Sync:
        def __init__(self, d):
            self.d = d

        def run(self, coro):
            return loop.run_until_complete(coro)

        def __getattr__(self, name):
            return getattr(self.d, name)

    yield Sync(database)
    loop.close()


@pytest.fixture(scope="session")
def recruit_client():
    from member_auth import create_member_token
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {create_member_token(RECRUIT_USER, RECRUIT_EMAIL)}"
    return s


@pytest.fixture(scope="session")
def reactivation_client():
    from member_auth import create_member_token
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {create_member_token(REACT_USER, REACT_EMAIL)}"
    return s


# ---------- document_renderer unit tests ----------
class TestRendererUnit:
    def test_clean_document_text_strips_artifacts(self):
        from document_renderer import clean_document_text
        raw = "Sections:\nTitle: Our Mission\nContent: We serve youth.\nVersion 1\n- first bullet\nnormal body"
        out = clean_document_text(raw, "Board Opportunity")
        for artifact in ARTIFACTS:
            assert artifact not in out, f"{artifact} survived cleaning: {out}"
        assert "OUR MISSION" in out           # Title: -> heading (uppercased)
        assert "We serve youth." in out       # Content: -> body
        assert "- first bullet" in out
        assert "normal body" in out

    def test_clean_document_lines_kinds(self):
        from document_renderer import clean_document_lines
        blocks = clean_document_lines("Title: Roles\nContent: text here\nSECTION HEAD\n- bullet", "X")
        kinds = [k for k, _ in blocks]
        assert kinds == ["heading", "body", "heading", "bullet"], blocks

    def test_render_pdf_cover_and_created_by(self):
        from document_renderer import render_document_pdf
        pdf = render_document_pdf(
            title="QA Standard Doc", org_name="QA Nonprofit",
            body_text="Sections:\nTitle: Purpose\nContent: Body sentence.\nVersion 1\n- bullet one",
            branding={"primary_color": "#7a1f2b"},
            created_by={"name": "Jane Doe", "title": "Founder", "organization": "QA Nonprofit"},
            prepared_for="Sam Candidate")
        assert pdf[:4] == b"%PDF"
        text, pages = pdf_text(pdf)
        assert pages >= 2, f"expected cover + content, got {pages}"
        assert "QA Standard Doc" in text
        assert "Prepared for Sam Candidate" in text
        assert "Created By" in text and "Jane Doe" in text
        assert "Page 1" in text
        for artifact in ARTIFACTS:
            assert artifact not in text, f"{artifact} present in PDF"

    def test_brand_color_fallback_black(self):
        from document_renderer import brand_color
        assert brand_color({}) == "#000000"
        assert brand_color({"primary_color": "notahex"}) == "#000000"
        assert brand_color({"primary_color": "#7A1F2B"}) == "#7A1F2B"

    def test_brand_color_from_logo_dominant_color(self):
        """Generated 8x8 pure-red PNG data URL -> derived brand color, no primary_color set."""
        from document_renderer import brand_color, _logo_dominant_color
        raw = _png_bytes((200, 30, 30))
        data_url = "data:image/png;base64," + base64.b64encode(raw).decode()
        derived = _logo_dominant_color(data_url)
        assert derived.startswith("#") and len(derived) == 7, derived
        r = int(derived[1:3], 16)
        assert r > 150, f"expected red-dominant color, got {derived}"
        assert brand_color({"logo_data": data_url}) == derived
        assert brand_color({"logo_data": "data:image/png;base64,notvalid"}) == "#000000"

    def test_render_pdf_with_logo(self):
        from document_renderer import render_document_pdf
        data_url = "data:image/png;base64," + base64.b64encode(_png_bytes((30, 60, 200))).decode()
        pdf = render_document_pdf(title="Logo Doc", org_name="Org", body_text="Body line.",
                                  branding={"logo_data": data_url}, created_by={"name": "A B"})
        text, pages = pdf_text(pdf)
        assert pdf[:4] == b"%PDF" and pages >= 2
        assert "Logo Doc" in text and "Created By" in text


def _png_bytes(rgb):
    """Minimal 8x8 solid-color PNG."""
    width = height = 8
    rows = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind, data):
        import struct
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    import struct
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


# ---------- Material PDF endpoint ----------
class TestMaterialPdf:
    def test_material_pdf_standard(self, recruit_client, db):
        resp = recruit_client.get(f"{BASE_URL}/api/workspace/material-pdf/{RECRUIT_MATERIAL}")
        assert resp.status_code == 200, resp.text[:300]
        assert resp.headers["content-type"].startswith("application/pdf")
        text, pages = pdf_text(resp.content)
        assert pages >= 2, f"pages={pages}"
        assert "Board Opportunity" in text
        assert "Page 1" in text
        assert "Created By" in text
        for artifact in ARTIFACTS:
            assert artifact not in text, f"{artifact} present in material PDF"

    def test_material_pdf_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/workspace/material-pdf/{RECRUIT_MATERIAL}")
        assert resp.status_code in (401, 403), resp.status_code

    def test_material_pdf_unknown_id_404(self, recruit_client):
        resp = recruit_client.get(f"{BASE_URL}/api/workspace/material-pdf/does-not-exist")
        assert resp.status_code == 404


# ---------- Strategy PDF endpoint (QA-seeded strategy material, cleaned up) ----------
class TestStrategyPdf:
    QA_ID = "QA_ITER51_strategy"

    @pytest.fixture(scope="class", autouse=True)
    def seed(self, db):
        db.run(db.generated_materials.insert_one({
            "material_id": self.QA_ID, "user_id": RECRUIT_USER, "type": "recruitment_strategy",
            "application_id": "", "module": 2, "title": "Board Recruitment Strategy",
            "current_version": 1, "status": "Generated",
            "versions": [{"version": 1, "display_text": "Sections:\nVersion 1", "structured": {
                "executive_summary": "Summary paragraph for QA.",
                "roles": [{"role_name": "Treasurer", "person_sought": "CPA with nonprofit experience"}],
                "channels": [{"channel": "linkedin", "approach": "Targeted outreach"}],
                "selection_criteria": ["Mission alignment"],
            }}],
        }))
        yield
        db.run(db.generated_materials.delete_one({"material_id": self.QA_ID}))

    def test_strategy_pdf(self, recruit_client):
        resp = recruit_client.get(f"{BASE_URL}/api/workspace/strategy-pdf")
        assert resp.status_code == 200, resp.text[:300]
        assert resp.headers["content-type"].startswith("application/pdf")
        text, pages = pdf_text(resp.content)
        assert pages >= 2
        assert "Board Recruitment Strategy" in text
        assert "1. BOARD MEMBERS WE ARE RECRUITING" in text.upper()
        assert "2. RECRUITMENT CHANNELS" in text.upper()
        assert "3. SELECTION CRITERIA" in text.upper()
        assert "Created By" in text
        for artifact in ARTIFACTS:
            assert artifact not in text, f"{artifact} present in strategy PDF"


# ---------- Reactivation PDF endpoint ----------
class TestReactivationPdf:
    def test_reactivation_material_pdf(self, reactivation_client, db):
        material = db.run(db.generated_materials.find_one({"material_id": REACT_MATERIAL}, {"_id": 0, "application_id": 1, "title": 1}))
        record = db.run(db.reactivation_board_members.find_one({"member_record_id": material["application_id"]}, {"_id": 0, "name": 1}))
        resp = reactivation_client.get(f"{BASE_URL}/api/reactivation/materials/{REACT_MATERIAL}/pdf")
        assert resp.status_code == 200, resp.text[:300]
        assert resp.headers["content-type"].startswith("application/pdf")
        text, pages = pdf_text(resp.content)
        assert pages >= 2
        assert material["title"] in text
        assert "Page 1" in text
        assert "Created By" in text
        if record and record.get("name"):
            assert f"Prepared for {record['name']}" in text, text[:600]
        for artifact in ARTIFACTS:
            assert artifact not in text, f"{artifact} present in reactivation PDF"


# ---------- Shared resource API ----------
class TestSharedApi:
    def test_shared_includes_created_by_and_clean_text(self):
        resp = requests.get(f"{BASE_URL}/api/shared/{SHARE_TOKEN}")
        assert resp.status_code == 200, resp.text[:300]
        data = resp.json()
        assert "_id" not in data
        assert set(["title", "display_text", "organization_name", "created_by"]).issubset(data.keys())
        created_by = data["created_by"]
        assert set(["name", "title", "organization"]).issubset(created_by.keys())
        assert created_by["name"], created_by
        for artifact in ARTIFACTS:
            assert artifact not in data["display_text"], f"{artifact} in shared display_text"

    def test_shared_unknown_token_404(self):
        resp = requests.get(f"{BASE_URL}/api/shared/nope-not-a-token")
        assert resp.status_code == 404


# ---------- Regression ----------
class TestRegression:
    def test_backend_health(self):
        resp = requests.get(f"{BASE_URL}/api/")
        assert resp.status_code in (200, 404), resp.status_code

    def test_sign_token_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/public/sign/b31b7be665da4e5e878bf50c306c4860")
        assert resp.status_code == 200, resp.text[:300]
        data = resp.json()
        assert data.get("agreement_title")
        assert data.get("board_member_name")
        assert isinstance(data.get("document"), str) and data["document"]
