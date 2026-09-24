from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Homepage Applicant Network contract failed: missing {label}")

home = read("frontend/src/pages/MainHomePage.jsx")
app = read("frontend/src/App.js")
contract = read("CLEAN_HOUSE_CONTRACT.md")

require(app, 'path="/join-a-board"', "Board Applicant Network route")
require(home, 'data-testid="home-board-applicant-network"', "Board Applicant Network homepage card")
require(home, 'to="/join-a-board"', "homepage Board Applicant Network link")
require(home, 'data-testid="home-closing-join-board-network"', "closing Board Applicant Network CTA")
require(home, "JOIN THE BOARD APPLICANT NETWORK", "Board Applicant Network CTA copy")
require(contract, "a full pathway card alongside the other homepage pathways", "homepage pathway contract")
require(contract, "a second call-to-action in the final homepage CTA section", "closing CTA contract")

print("Homepage Board Applicant Network contract: PASS")
