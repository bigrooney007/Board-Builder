"""Fail if the recovery changes touch application files outside the agreed scope."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "d627263044f606a819366d3b04fe7e240b8e254d"
ALLOWED = {
    "backend/clean_platform_routes.py",
    "frontend/src/App.js",
    "frontend/src/admin/HomepageTextSection.jsx",
    "frontend/src/clean/platform.js",
    "frontend/src/components/DemoOfferCards.jsx",
    "frontend/src/content/offerTextDefaults.js",
    "frontend/src/funnels/GuidedProductPages.jsx",
    "frontend/src/funnels/OfferTextRoadmap.jsx",
    "frontend/src/funnels/RecruitWalkthroughPage.jsx",
    "frontend/src/funnels/RecruitmentHomePage.jsx",
    "frontend/src/game/GameUpgradePage.jsx",
    "frontend/src/member/RecruitCampaignMaterialsPage.jsx",
    "frontend/src/member/RecruitCampaignSetupPage.jsx",
    "frontend/src/pages/AdminPage.jsx",
    "frontend/src/admin/RecoveredOffers.test.jsx",
    "frontend/src/game/GuidedUpgrade.test.jsx",
    "backend/tests/test_four_customer_journeys_contract.py",
    "backend/tests/test_recovered_offer_content.py",
    "backend/tests/test_recovered_recruitment_routes.py",
    ".github/workflows/recovered-offer-validation.yml",
    "tests/recovered_jest_setup.cjs",
    "tests/recovered_offer_app.py",
    "tests/recovered_offer_browser.py",
    "tests/validate_recovered_offer_scope.py",
    "docs/recovered-offer-release.md",
}
changed = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
unexpected = set(changed) - ALLOWED
assert not unexpected, f"Out-of-scope changes: {sorted(unexpected)}"
assert not (ROOT / "frontend/src/v2").exists(), "V2 application files must not be present"
assert not list((ROOT / "backend").glob("v2_*.py")), "V2 backend files must not be present"
print(f"Recovery scope PASS: {len(changed)} files reviewed; original homepage, CSS, questionnaires, dashboards, AI and payment services unchanged.")
