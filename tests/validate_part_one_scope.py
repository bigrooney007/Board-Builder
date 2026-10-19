"""Guard the authorized Part One change against the actual starting release."""
import ast
import re
import subprocess
from pathlib import Path

BASE = "549b3d2db5b6fdf96ae9a396d4e141df3fd77622"
ROOT = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)
def original(path):
    return git("show", BASE + ":" + path)

protected = [
    "backend/fundraising_launch.py", "backend/fundraising_launch_content.json", "backend/fundraising_audiences.py",
    "backend/game_routes.py", "backend/game_night_routes.py", "backend/group_game_routes.py", "backend/game_meeting_routes.py",
    "backend/strategy_routes.py", "backend/strategic_planning_routes.py", "backend/strategic_questionnaire.py",
    "backend/guided_product_routes.py", "backend/marketing_routes.py", "backend/blog_service.py", "backend/blog_feed.py",
    "frontend/src/funnels/RecruitmentHomePage.jsx", "frontend/src/funnels/RecruitFreePage.jsx",
    "frontend/src/funnels/RecruitQuestionsPage.jsx", "frontend/src/funnels/GuidedProductPages.jsx",
    "frontend/src/game/FundraisingSetup.jsx", "frontend/src/game/FundraisingWorkspace.jsx",
    "frontend/src/game/GroupGamePage.jsx", "frontend/src/game/GroupPlayPage.jsx", "frontend/src/game/StrategyPage.jsx",
    "frontend/src/game/AudienceQuestionnaire.jsx", "frontend/src/admin/FacilitatorWorkspace.jsx",
    "frontend/src/content/testimonials.js", "frontend/src/pages/MainHomePage.css", "frontend/yarn.lock",
]
for path in protected:
    assert (ROOT / path).read_text() == original(path), path + " changed outside Part One"

def line_items(source):
    return [ast.dump(value, include_attributes=False) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Dict)
            for key, value in zip(node.keys, node.values) if isinstance(key, ast.Constant) and key.value == "line_items"]
assert line_items((ROOT / "backend/payment_routes.py").read_text()) == line_items(original("backend/payment_routes.py")), "An existing checkout changed"
route_paths = lambda text: set(re.findall(r'<Route\s+path=([^>]+?)\s+element=', text))
assert route_paths(original("frontend/src/App.js")) <= route_paths((ROOT / "frontend/src/App.js").read_text()), "An existing route was removed"
changed = git("diff", "--name-only", BASE, "HEAD").splitlines()
assert not any("/v2/" in p or "autofundraiser" in p.lower() for p in changed), "Another application or V2 changed"
subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT, check=True)
print("PASS Part One scope: existing product flows, prices, questions, meeting tools, testimonials, blog infrastructure and routes preserved")
