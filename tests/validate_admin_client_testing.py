from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Admin client testing contract failed: missing {label}")

def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Admin client testing contract failed: found unsafe {label}")

preview_backend = read("backend/admin_dashboard_preview_routes.py")
preview_ui = read("frontend/src/admin/DashboardPreviewSection.jsx")
platform = read("frontend/src/clean/platform.js")
analytics = read("backend/clean_platform_routes.py")
admin_page = read("frontend/src/pages/AdminPage.jsx")
server = read("backend/server.py")

require(preview_backend, 'router = APIRouter(prefix="/api/admin/dashboard-preview")', "Admin preview router")
require(preview_backend, '@router.post("/fresh/{product}")', "fresh client test launcher")
require(preview_backend, '@router.post("/{product}")', "fully preloaded launcher")
require(preview_backend, 'admin = await authenticate_admin(request, db)', "Admin authentication on launchers")
require(preview_backend, "internal_admin_entitlement", "isolated internal member entitlement")
require(preview_backend, "internal_client_test", "fresh client test identity")
require(preview_backend, 'set_member_cookie(response, create_member_token(member["user_id"], member["email"]))', "real member session issuance")
for product in ("recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment"):
    require(preview_backend, f'"{product}": {{', f"product config {product}")
    require(preview_ui, f'key: "{product}"', f"Admin testing card {product}")

require(preview_backend, 'FRESH_TEST_VERSION = "fresh-v1"', "fresh fixture version")
require(preview_backend, '"amount": 0', "zero-value internal payment record")
require(preview_backend, '"internal_preview": True', "internal preview marker")
require(preview_backend, 'return f"/recruit/welcome?session_id={session_id}"', "Recruitment post-payment welcome")
require(preview_backend, 'return "/game/welcome"', "Fundraising Game post-payment welcome")
require(preview_backend, 'return f"/{product}/welcome?session_id={session_id}"', "guided product post-payment welcome")
require(preview_backend, '"new_members_needed": "3"', "Recruitment homepage context")
require(preview_backend, "recruitment_answers", "prefilled Recruitment client-test questions")
require(preview_backend, '"goal": {', "Fundraising Game homepage goal context")
require(preview_backend, '"guided_lead_token": lead_token', "Strategic/Recommitment paid guided session")

require(preview_ui, "Client Testing Center", "Client Testing Center heading")
require(preview_ui, "START FRESH CLIENT TEST", "fresh test button")
require(preview_ui, "OPEN FULLY PRELOADED JOURNEY", "preloaded test button")
require(preview_ui, '/admin/dashboard-preview/fresh/', "fresh Admin API call")
require(preview_ui, '/admin/dashboard-preview/', "preloaded Admin API call")
require(preview_ui, 'sessionStorage.setItem("adminClientTest", "1")', "QA analytics suppression marker")

require(platform, 'sessionStorage.getItem("adminClientTest") === "1"', "client-side QA analytics suppression")
require(analytics, '{"internal_preview": {"$ne": True}}', "payment analytics internal-preview exclusion")
require(admin_page, 'sessionStorage.removeItem("adminClientTest")', "QA analytics reset on Admin return")

require(preview_backend, '"board-recommitment": {', "Recommitment product config")
require(preview_backend, '"dashboard_path": "/board-recommitment/dashboard"', "Recommitment preloaded dashboard")
require(preview_backend, '"purchase_source": "board_recommitment_497"', "Recommitment fresh paid-session contract")
require(preview_ui, 'key: "board-recommitment"', "Recommitment Admin card")

forbid(preview_backend, 'password_hash": admin', "Admin password reuse")
forbid(preview_backend, 'password": admin', "Admin password copying")
require(preview_backend, '"password_hash": ""', "passwordless isolated preview identity")
require(server, "create_admin_dashboard_preview_router", "Admin testing router mounted in server")

print("Admin client testing center contract: PASS")
