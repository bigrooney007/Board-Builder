"""Release guard for targeted updates to the recovered original application."""
import ast
import re
import subprocess
from pathlib import Path
BASE="a33a64082199fd6c508b0360552bdadf5c9ee5c3"
ROOT=Path(__file__).resolve().parents[1]

def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True)
def original(path):return git("show",BASE+":"+path)

# Landing-page design, shared visual styles, prices, and original route destinations
# are independent of the authorized questionnaire and testing changes.
for path in ("frontend/src/pages/MainHomePage.jsx","frontend/src/funnels/RecruitmentHomePage.jsx",
             "frontend/src/funnels/GuidedProductPages.jsx","frontend/src/game/GamePublicLanding.jsx"):
    if (ROOT/path).exists():assert (ROOT/path).read_text()==original(path),path+" unexpectedly changed"
changed=git("diff","--name-only",BASE,"HEAD").splitlines()
assert not any(p.endswith(".css") or "/v2/" in p or "autofundraiser" in p.lower() for p in changed),changed
app=(ROOT/"frontend/src/App.js").read_text()
paths=lambda text:re.findall(r'<Route\s+path=([^>]+?)\s+element=',text)
assert paths(app)==paths(original("frontend/src/App.js")),"Original customer route destinations changed"

def price_lines(text):
    return [ast.dump(value,include_attributes=False) for node in ast.walk(ast.parse(text)) if isinstance(node,ast.Dict)
            for key,value in zip(node.keys,node.values) if isinstance(key,ast.Constant) and key.value=="line_items"]
assert price_lines((ROOT/"backend/payment_routes.py").read_text())==price_lines(original("backend/payment_routes.py")),"Checkout prices/providers changed"
subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT,check=True)
assert not (ROOT/"frontend/src/v2").exists(),"Unwanted V2 directory present"
print("PASS: original homepage, landing designs, CSS, route destinations, checkout line items and recovered ancestry preserved")
