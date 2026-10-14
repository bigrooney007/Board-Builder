"""Verify V2 isolation and preservation against the exact authorized Git base.

These source checks supplement the HTTP API and browser acceptance tests. They
are not a substitute for exercising the original application in staging.
"""

import ast
from io import BytesIO
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = "d627263044f606a819366d3b04fe7e240b8e254d"


def base_bytes(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


def current(path):
    return (ROOT / path).read_text(encoding="utf-8")


def python_routes(source):
    tree = ast.parse(source)
    routes = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr
            if method not in {"get", "post", "put", "delete", "patch", "options", "head"}:
                continue
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                routes.add((method, decorator.args[0].value, node.name))
    return routes


class V2SourceContracts(unittest.TestCase):
    def test_existing_contract_results_match_the_exact_original_base(self):
        validators = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE, "tests"], cwd=ROOT, text=True).splitlines()
        validators = [path for path in validators if Path(path).name.startswith("validate_") and path.endswith(".py")]
        self.assertGreaterEqual(len(validators), 10)
        with tempfile.TemporaryDirectory(prefix="nbb-v2-original-contracts-") as directory:
            archive = subprocess.check_output(["git", "archive", BASE], cwd=ROOT)
            with tarfile.open(fileobj=BytesIO(archive)) as tree:
                tree.extractall(directory, filter="data")
            for path in validators:
                with self.subTest(path=path):
                    before = subprocess.run(["python", str(Path(directory) / path)], capture_output=True, text=True)
                    after = subprocess.run(["python", str(ROOT / path)], capture_output=True, text=True)
                    self.assertEqual((before.returncode, before.stdout, before.stderr),
                                     (after.returncode, after.stdout, after.stderr),
                                     f"Existing contract behavior changed: {path}")

    def test_main_homepage_preserved_except_authorized_education_destinations(self):
        path = "frontend/src/pages/MainHomePage.jsx"
        expected = base_bytes(path).decode().replace(
            "{ FREE_START_LABEL, PUBLIC_START_ROUTES }", "{ FREE_START_LABEL }")
        replacements = {
            "PUBLIC_START_ROUTES.recruitment": '"/v2/recruit"',
            'PUBLIC_START_ROUTES["board-fundraising-game"]': '"/v2/board-fundraising-game"',
            'PUBLIC_START_ROUTES["strategic-planning"]': '"/v2/strategic-planning"',
            'PUBLIC_START_ROUTES["board-recommitment"]': '"/v2/board-recommitment"',
        }
        for original, target in replacements.items():
            self.assertEqual(expected.count(original), 1)
            expected = expected.replace(original, target)
        self.assertEqual(current(path), expected)
        self.assertEqual((ROOT / "frontend/src/pages/MainHomePage.css").read_bytes(),
                         base_bytes("frontend/src/pages/MainHomePage.css"))

    def test_homepage_services_lead_to_education_then_existing_free_questions(self):
        home = current("frontend/src/pages/MainHomePage.jsx")
        routes = current("frontend/src/v2/V2Routes.jsx")
        pages = current("frontend/src/v2/PublicPages.jsx")
        landing = current("frontend/src/v2/LandingContent.jsx")
        for slug in ("recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"):
            self.assertIn(f'start: "/v2/{slug}"', home)
        self.assertIn("to={meta.start || meta.to}", home)
        self.assertIn('<Route path="/v2/*" element={<V2Routes />} />', current("frontend/src/App.js"))
        self.assertIn('path=":product" element={protectedPage(<ProductLandingPage />)}', routes)
        self.assertIn('path=":product/start" element={protectedPage(<FreeIntakePage />)}', routes)
        self.assertIn('const start = `/v2/${product}/start`', landing)
        self.assertIn('to={start}', landing)
        self.assertIn('Start for Free', landing)
        self.assertIn('<LandingContent product={product}', pages)
        for questions in ("RECRUITMENT_QUESTIONS", "STRATEGIC", "RECOMMITMENT", "FIVE_QUESTIONS"):
            self.assertIn(questions, pages)

    def test_original_customer_route_definitions_preserved(self):
        original = base_bytes("frontend/src/App.js").decode()
        live = current("frontend/src/App.js")
        routes = re.findall(r"<Route\b[^>]*(?:>[^\n]*)?", original)
        self.assertGreater(len(routes), 100)
        for route in routes:
            with self.subTest(route=route[:100]):
                self.assertIn(route, live)

    def test_original_backend_routes_preserved(self):
        tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE, "backend"], cwd=ROOT, text=True).splitlines()
        for path in tracked:
            if not path.endswith(".py") or "/tests/" in path:
                continue
            original = python_routes(base_bytes(path).decode())
            if original:
                with self.subTest(path=path):
                    self.assertTrue((ROOT / path).exists(), f"Original source deleted: {path}")
                    self.assertTrue(original <= python_routes(current(path)), f"Original API route removed from {path}")

    def test_historical_pricing_definitions_unchanged(self):
        before = ast.parse(base_bytes("backend/payment_routes.py").decode())
        after = ast.parse(current("backend/payment_routes.py"))
        wanted = {}
        actual = {}
        for tree, result in ((before, wanted), (after, actual)):
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("resolve_"):
                    result[node.name] = ast.dump(node, include_attributes=False)
                elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PRICE_ENV" for t in node.targets):
                    result["PRICE_ENV"] = ast.dump(node, include_attributes=False)
        self.assertEqual(wanted, actual)

    def test_original_purchase_and_entitlement_service_retained(self):
        for path in ("backend/member_routes.py", "backend/workspace_service.py", "backend/fbb_routes.py", "backend/board_fix_routes.py"):
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_bytes(), base_bytes(path))

    def test_no_auto_fundraiser_source_changes(self):
        paths = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
        self.assertFalse([p for p in paths if "autofundraiser" in p.lower() or "auto_fundraiser" in p.lower()])

    def test_v2_customer_navigation_has_no_old_workspace_links(self):
        files = list((ROOT / "frontend/src/v2").glob("*.jsx"))
        self.assertTrue(files, "V2 customer pages must exist")
        patterns = [
            r"(?:to|href)\s*=\s*[\"']/(?:app|game/dashboard|member|portfolio)(?:/|[\"'])",
            r"navigate\(\s*[\"']/(?:app|game/dashboard|member|portfolio)(?:/|[\"'])",
        ]
        for path in files:
            if path.name.startswith("Admin"):
                continue
            with self.subTest(path=path.name):
                for pattern in patterns:
                    self.assertIsNone(re.search(pattern, path.read_text()), "V2 customer route leads to an old workspace")


if __name__ == "__main__":
    unittest.main(verbosity=2)
