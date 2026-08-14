"""Iteration 37 — cross-product architecture verification.

Covers:
  A. Six-module recruitment course (basic + self-guided) & module 6 progress
  B. Accountability STAGES range (module1..module6) — unit test
  C. Board Transformation diagnostic API (rules, ordering, select, no nurture)
  D. Reactivation course unchanged (5 modules)
  E. Recruitment funnel still writes a nurture contact
"""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

MODULE_TESTER = {"email": "module-tester@example.com", "password": "ModuleTest123!"}


@pytest.fixture(scope="module")
def module_tester_token():
    r = requests.post(f"{BASE}/api/members/login", json=MODULE_TESTER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ---------- A. Recruitment course structure ----------
class TestRecruitmentCourse:
    def test_self_guided_six_modules(self, module_tester_token):
        r = requests.get(f"{BASE}/api/courses/recruitment/self-guided",
                         headers={"Authorization": f"Bearer {module_tester_token}"}, timeout=30)
        assert r.status_code == 200
        modules = r.json()["modules"]
        assert len(modules) == 6
        titles = [m["title"] for m in modules]
        assert titles[0] == "Recruiting Board Members the Right Way"
        assert titles[1] == "Identify the Board Members Your Organization Needs"
        assert titles[2] == "Launch Your Recruitment Campaign"
        assert titles[3] == "Select and Interview Your Applicants"
        assert titles[4] == "Complete References and Background Checks"
        assert titles[5] == "Onboard Your New Board Members"
        assert modules[0].get("kind") == "training"
        # Module 1 has no youtube video (training placeholder)
        assert modules[0].get("youtube_url", "") == ""
        # Video remap
        assert "Crzh5tPpQYo" in modules[1]["youtube_url"]
        assert "E4S16dkgKSY" in modules[2]["youtube_url"]
        assert "WxGpi3hHEO8" in modules[3]["youtube_url"]
        assert "-gbn1_sl9h8" in modules[4]["youtube_url"]
        assert "fdjjsiEnfWc" in modules[5]["youtube_url"]

    def test_basic_six_modules(self, module_tester_token):
        r = requests.get(f"{BASE}/api/courses/recruitment/basic",
                         headers={"Authorization": f"Bearer {module_tester_token}"}, timeout=30)
        assert r.status_code == 200
        modules = r.json()["modules"]
        assert len(modules) == 6
        assert modules[0]["title"] == "Recruiting Board Members the Right Way"
        assert modules[0].get("youtube_url", "") == ""
        assert "fdjjsiEnfWc" in modules[5]["youtube_url"]

    def test_progress_module_6_accepted(self, module_tester_token):
        """Regression: was le=5 → 422. After fix, module 6 must be accepted."""
        r = requests.post(f"{BASE}/api/courses/progress",
                          headers={"Authorization": f"Bearer {module_tester_token}"},
                          json={"product": "recruitment_self_guided", "module_number": 6, "action": "viewed"},
                          timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ok"
        # cleanup
        requests.post(f"{BASE}/api/courses/progress",
                      headers={"Authorization": f"Bearer {module_tester_token}"},
                      json={"product": "recruitment_self_guided", "module_number": 6, "action": "uncompleted"},
                      timeout=30)

    def test_progress_module_1_complete_percent_over_6(self, module_tester_token):
        r = requests.post(f"{BASE}/api/courses/progress",
                          headers={"Authorization": f"Bearer {module_tester_token}"},
                          json={"product": "recruitment_self_guided", "module_number": 1, "action": "completed"},
                          timeout=30)
        assert r.status_code == 200
        # ceil(1/6*100)=17
        assert r.json()["percent_complete"] in (16, 17)
        # cleanup: uncomplete
        requests.post(f"{BASE}/api/courses/progress",
                      headers={"Authorization": f"Bearer {module_tester_token}"},
                      json={"product": "recruitment_self_guided", "module_number": 1, "action": "uncompleted"},
                      timeout=30)


# ---------- D. Reactivation course unchanged ----------
class TestReactivationCourse:
    def test_reactivation_5_modules(self):
        r = requests.post(f"{BASE}/api/members/login",
                          json={"email": "test_ui_batch2_6ca82f@example.com", "password": "UITest123!"}, timeout=30)
        assert r.status_code == 200
        tok = r.json()["token"]
        r = requests.get(f"{BASE}/api/courses/reactivation/self-guided",
                         headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 200
        assert len(r.json()["modules"]) == 5


# ---------- B. Accountability stage remap (unit) ----------
class TestAccountabilityStages:
    def test_stages_module1_to_6(self):
        import sys, importlib
        sys.path.insert(0, "/app/backend")
        acc = importlib.import_module("accountability_service")
        for i in range(1, 7):
            assert f"module{i}" in acc.STAGES, f"module{i} missing from STAGES"
            assert acc.STAGES[f"module{i}"]["module"] == i

    def test_current_stage_iterates_1_to_7(self):
        import inspect, importlib
        acc = importlib.import_module("accountability_service")
        src = inspect.getsource(acc.current_stage)
        assert "range(1, 7)" in src, "current_stage should iterate 1..6 (range(1,7))"


# ---------- C. Board Transformation diagnostic rules ----------
_leads_to_cleanup = []


def _bt_payload(answers):
    return {
        "name": "TEST_iter37 Diag",
        "email": "delivered@resend.dev",
        "phone": "555-000",
        "organization": "TEST_iter37 Org",
        "answers": answers,
    }


class TestBoardTransformationRules:
    def _create(self, answers, expected_code=201):
        r = requests.post(f"{BASE}/api/funnel-leads/board_transformation",
                          json=_bt_payload(answers), timeout=30)
        assert r.status_code == expected_code, r.text
        if expected_code == 201:
            _leads_to_cleanup.append(r.json()["result_token"])
            return r.json()
        return r.json()

    def _result(self, token):
        r = requests.get(f"{BASE}/api/funnel-leads/result/{token}", timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    def test_active_greater_than_total_422(self):
        r = requests.post(f"{BASE}/api/funnel-leads/board_transformation",
                          json=_bt_payload({"present_board": 5, "active_board": 10,
                                            "need_recruit": "No", "reactivate_inactive": "No",
                                            "board_fundraising_now": "Yes — most do",
                                            "want_fundraising": "No"}), timeout=30)
        assert r.status_code == 422

    def test_zero_zero_accepted(self):
        c = self._create({"present_board": 0, "active_board": 0,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        res = self._result(c["result_token"])["result"]
        assert res["present_board"] == 0
        assert res["recommendations"] == []

    def test_recruit_yes_fires(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "Yes", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert self._result(c["result_token"])["result"]["recommendations"] == ["recruit"]

    def test_recruit_not_sure_fires(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "Not Sure", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert "recruit" in self._result(c["result_token"])["result"]["recommendations"]

    def test_recruit_no_does_not_fire(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert "recruit" not in self._result(c["result_token"])["result"]["recommendations"]

    def test_reactivate_requires_present_gt_active(self):
        # active==present → no reactivate even if user says Yes
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "Yes — all of them if possible",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert "reactivate" not in self._result(c["result_token"])["result"]["recommendations"]

    def test_reactivate_fires_present_gt_active(self):
        c = self._create({"present_board": 8, "active_board": 3,
                          "need_recruit": "No", "reactivate_inactive": "Yes — some of them",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert "reactivate" in self._result(c["result_token"])["result"]["recommendations"]

    def test_activate_want_no_does_not_fire(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "No", "want_fundraising": "No"})
        assert "activate" not in self._result(c["result_token"])["result"]["recommendations"]

    def test_activate_fires_when_want_yes_and_now_not_most(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "Some do", "want_fundraising": "Yes"})
        assert "activate" in self._result(c["result_token"])["result"]["recommendations"]

    def test_activate_does_not_fire_when_now_most_do(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "Yes"})
        assert "activate" not in self._result(c["result_token"])["result"]["recommendations"]

    def test_ordering_reactivate_recruit_activate(self):
        c = self._create({"present_board": 10, "active_board": 3,
                          "need_recruit": "Yes",
                          "reactivate_inactive": "Yes — all of them if possible",
                          "board_fundraising_now": "Very little", "want_fundraising": "Yes"})
        recs = self._result(c["result_token"])["result"]["recommendations"]
        assert recs == ["reactivate", "recruit", "activate"], recs

    def test_empty_recommendations_possible(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "No", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        assert self._result(c["result_token"])["result"]["recommendations"] == []

    def test_no_nurture_contact_created(self):
        # Use a unique email to detect whether sync_lead_nurture created a doc
        email = f"test_iter37_bt_{int(time.time())}@example.com"
        payload = _bt_payload({"present_board": 5, "active_board": 5,
                               "need_recruit": "No", "reactivate_inactive": "No",
                               "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        payload["email"] = email
        r = requests.post(f"{BASE}/api/funnel-leads/board_transformation", json=payload, timeout=30)
        assert r.status_code == 201
        _leads_to_cleanup.append(r.json()["result_token"])
        # Check DB directly
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _check():
            c = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            doc = await c[os.environ.get("DB_NAME", "test_database")].nurture_contacts.find_one(
                {"email": email.lower()})
            return doc
        doc = asyncio.run(_check())
        assert doc is None, f"board_transformation should NOT create nurture_contact but got: {doc}"

    def test_result_token_wrong_404(self):
        r = requests.get(f"{BASE}/api/funnel-leads/result/does-not-exist-token", timeout=30)
        assert r.status_code == 404

    def test_select_product_ok(self):
        c = self._create({"present_board": 5, "active_board": 5,
                          "need_recruit": "Yes", "reactivate_inactive": "No",
                          "board_fundraising_now": "Yes — most do", "want_fundraising": "No"})
        r = requests.post(f"{BASE}/api/funnel-leads/board-transformation/select",
                          json={"result_token": c["result_token"], "product": "reactivate"}, timeout=30)
        assert r.status_code == 200
        # invalid product
        r = requests.post(f"{BASE}/api/funnel-leads/board-transformation/select",
                          json={"result_token": c["result_token"], "product": "junk"}, timeout=30)
        assert r.status_code == 422
        # bad token
        r = requests.post(f"{BASE}/api/funnel-leads/board-transformation/select",
                          json={"result_token": "nonexistent-token-xyz", "product": "recruit"}, timeout=30)
        assert r.status_code == 404


# ---------- E. Recruitment funnel still creates nurture ----------
class TestRecruitmentFunnelNurture:
    def test_recruitment_lead_creates_nurture_contact(self):
        email = f"test_iter37_rec_{int(time.time())}@example.com"
        payload = {
            "name": "TEST_iter37 rec",
            "email": email,
            "phone": "555-111",
            "organization": "TEST_iter37 Rec Org",
            "answers": {
                "new_members_needed": "3",
                "support_preference": "diy",
                "accomplish_areas": ["Fundraising"],
                "present_board": 5,
                "active_board": 5,
            },
        }
        r = requests.post(f"{BASE}/api/funnel-leads/recruitment", json=payload, timeout=30)
        assert r.status_code == 201, r.text
        _leads_to_cleanup.append(r.json()["result_token"])
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _check():
            c = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            doc = await c[os.environ.get("DB_NAME", "test_database")].nurture_contacts.find_one(
                {"email": email.lower()})
            # cleanup
            await c[os.environ.get("DB_NAME", "test_database")].nurture_contacts.delete_one(
                {"email": email.lower()})
            return doc
        doc = asyncio.run(_check())
        assert doc is not None, "recruitment funnel should create nurture_contact"
        assert doc["active_offer_source"] == "recruitment"


# ---------- teardown cleanup of created board_transformation leads ----------
@pytest.fixture(scope="module", autouse=True)
def _cleanup_leads():
    yield
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    async def _clean():
        c = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = c[os.environ.get("DB_NAME", "test_database")]
        if _leads_to_cleanup:
            r = await db.funnel_leads.delete_many({"result_token": {"$in": _leads_to_cleanup}})
            print(f"cleaned {r.deleted_count} funnel_leads")
        # also clean any TEST_iter37 leads
        await db.funnel_leads.delete_many({"organization": {"$regex": "^TEST_iter37"}})
    asyncio.run(_clean())
