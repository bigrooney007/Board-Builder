"""Current questionnaire, meeting, approval, test-isolation and compatibility checks."""
import asyncio
import copy
import json
import os
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"));sys.path.insert(0,str(ROOT))
import strategic_questionnaire as sp
import fundraising_audiences as fg

class QuestionConfiguration(unittest.TestCase):
    def test_fifteen_exact_shared_planning_questions_without_mission_question(self):
        self.assertEqual(len(sp.QUESTIONS),15)
        form=sp.form_content()
        self.assertEqual([q["prompt"] for s in form["sections"] for q in s["questions"]],[q["prompt"] for q in sp.QUESTIONS])
        self.assertFalse(any("mission" in q["prompt"].lower() for q in sp.QUESTIONS))
    def test_selected_ideas_only_and_preserve_original_source(self):
        people=[{"participant_id":"one","name":"A","response":{sp.KEYS[0]:"Adopted proposal\n\nRejected proposal"}}]
        sections=sp.session_sections(people,{})
        areas=sp.adopted_areas(sections,{sp.KEYS[0]:[sections[0]["ideas"][0]["idea_id"]]})
        self.assertIn("Adopted proposal",sp.approved_context(areas,"Stored mission"))
        self.assertNotIn("Rejected proposal",sp.approved_context(areas))
        self.assertIn("Rejected proposal",sections[0]["ideas"][0]["source_response"])
        with self.assertRaises(ValueError):sp.adopted_areas(sections,{sp.KEYS[0]:"__use_all_ideas__"})
    def test_changed_decisions_invalidate_acknowledgement_revision(self):
        self.assertNotEqual(sp.decision_revision([{"text":"a"}]),sp.decision_revision([{"text":"b"}]))
    def test_fundraising_all_categories_can_be_skipped(self):
        result=fg.clean_response({"audiences":{},"category_status":{c:"complete" for c in fg.CATEGORIES},"involvement":"I can help with introductions."},submitting=True)
        self.assertTrue(all(result["audiences"][c]==[] for c in fg.CATEGORIES))
    def test_multiple_audiences_are_independent_and_uncertainty_allowed(self):
        from current_workflow_fixtures import fundraising_answers
        value=fundraising_answers();second=copy.deepcopy(value["audiences"]["individuals"][0]);second.update(id="other",who_why="Other people",amount="I am unsure.")
        value["audiences"]["individuals"].append(second)
        result=fg.clean_response(value,submitting=True)
        self.assertEqual(len(result["audiences"]["individuals"]),2)
        self.assertNotEqual(result["audiences"]["individuals"][0]["who_why"],second["who_why"])
    def test_incomplete_audience_and_duplicate_identifier_rejected(self):
        from fastapi import HTTPException
        from current_workflow_fixtures import fundraising_answers
        value=fundraising_answers();value["audiences"]["businesses"][0]["amount"]=""
        with self.assertRaises(HTTPException):fg.clean_response(value,submitting=True)
        value=fundraising_answers();value["audiences"]["businesses"][0]["id"]=value["audiences"]["individuals"][0]["id"]
        with self.assertRaises(HTTPException):fg.clean_response(value)

@unittest.skipUnless(os.environ.get("RECOVERY_ACCEPTANCE")=="1","Requires isolated local Mongo and fake providers")
class CurrentJourneyHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests import current_workflow_app as fixture
        import httpx
        from member_auth import create_member_token
        from motor.motor_asyncio import AsyncIOMotorClient
        self.mongo=AsyncIOMotorClient(os.environ["MONGO_URL"])
        self.f=fixture;self.db=self.mongo.nbb_current_workflow_unit_tests
        self.app=fixture.build_app(self.db)
        for name in await self.db.list_collection_names():await self.db[name].delete_many({})
        await self.db.users.insert_one({"user_id":"acceptance-admin","email":"admin@example.test","role":"admin"})
        self.admin=fixture.create_access_token("acceptance-admin","admin@example.test")
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url="http://test")
        self.headers={"Authorization":"Bearer "+self.admin}
    async def asyncTearDown(self):
        await self.client.aclose()
        self.mongo.close()
    async def request(self,method,path,body=None,expected=200,headers=None):
        response=await self.client.request(method,"/api"+path,json=body,headers=headers or self.headers)
        self.assertEqual(response.status_code,expected,response.text[:1000])
        return response.json()
    async def launch(self,product,mode="loaded"):
        path="/admin/dashboard-preview/"+("fresh/" if mode=="fresh" else "intro/" if mode=="intro" else "")+product
        data=await self.request("POST",path)
        self.headers={"Authorization":"Bearer "+data["token"]}
        member=await self.request("GET","/members/me")
        self.user=member["member"]["user_id"]
        self.sid="current-test-"+self.user
        return data
    async def test_admin_routes_all_four_actual_client_destinations_and_version_parity(self):
        manifest=await self.request("GET","/admin/dashboard-preview/manifest")
        self.assertEqual(manifest["planning_questions"],sp.QUESTIONS)
        self.assertEqual(manifest["fundraising"],fg.configuration())
        for product in ("recruitment","board-fundraising-game","strategic-planning","board-recommitment"):
            for mode in ("fresh","loaded"):
                self.headers={"Authorization":"Bearer "+self.admin}
                result=await self.launch(product,mode)
                self.assertEqual(result["workflow_version"],manifest["workflows"][product])
                self.assertNotIn("/v2/",result.get("start_url",result["dashboard_url"]))
    async def test_planning_intro_paid_hydration_once_and_form_parity(self):
        await self.launch("strategic-planning","intro")
        token="lead-"+self.user
        ctx=await self.request("GET","/guided/context/"+token)
        self.assertEqual(ctx["questions"],sp.QUESTIONS)
        from current_workflow_fixtures import planning_answers
        answers=planning_answers()
        saved=await self.request("PUT",f"/guided/context/{token}/answers",{"answers":answers});self.assertTrue(saved["complete"])
        checkout=await self.request("POST","/payments/guided-checkout",{"origin_url":"http://test","result_token":token,"product":"strategic-planning"})
        self.assertIn(self.sid,checkout["checkout_url"])
        await self.request("GET",f"/guided/dashboard?session_id={self.sid}&product=strategic-planning")
        await self.request("POST","/guided/strategic-planning/prepare-form",{"session_id":self.sid})
        p=await self.db.sp_projects.find_one({"guided_session_id":self.sid})
        self.assertEqual(p["questionnaire_version"],sp.VERSION)
        person=await self.db.sp_participants.find_one({"project_id":p["project_id"],"role":"Lead User"})
        self.assertEqual(person["status"],"COMPLETED");self.assertEqual(person["response"],answers)
        result=await self.request("GET","/strategic-planning-form/"+person["form_token"])
        self.assertTrue(result["submitted"]);self.assertEqual(result["form"],sp.form_content())
        await self.request("GET",f"/guided/dashboard?session_id={self.sid}&product=strategic-planning")
        self.assertEqual(await self.db.sp_participants.count_documents({"project_id":p["project_id"],"role":"Lead User"}),1)
    async def test_planning_group_review_individual_adoption_selected_only_generation_and_email(self):
        await self.launch("strategic-planning")
        p=await self.db.sp_projects.find_one({"guided_session_id":self.sid});pid=p["project_id"]
        result=await self.request("GET",f"/guided/strategic-planning/session?session_id={self.sid}")
        self.assertEqual(len(result["sections"]),15)
        await self.request("POST","/guided/strategic-planning/session/start",{"session_id":self.sid})
        idea=result["sections"][0]["ideas"][0]["idea_id"]
        await self.request("POST","/guided/strategic-planning/session/decision",{"session_id":self.sid,"section_key":sp.KEYS[0],"decision":"__use_all_ideas__"},422)
        decisions={sp.KEYS[0]:[idea]}
        await self.request("POST","/guided/strategic-planning/session/decision",{"session_id":self.sid,"section_key":sp.KEYS[0],"decision":[idea]})
        review=await self.request("POST","/guided/strategic-planning/session/complete",{"session_id":self.sid,"decisions":decisions,"transcript":"Unapproved: invent a new mission and spend a million dollars"})
        self.assertEqual(review["status"],"REVIEW")
        person=await self.db.sp_participants.find_one({"project_id":pid,"role":"Board Member"})
        await self.request("POST","/guided/strategic-planning/session/acknowledge/"+person["form_token"],{"revision":"wrong","confirmed":True,"accept_responsibilities":True},409)
        await self.request("POST","/guided/strategic-planning/session/acknowledge/"+person["form_token"],{"revision":review["decision_revision"],"confirmed":True,"accept_responsibilities":True})
        self.assertEqual(await self.db.sp_participants.count_documents({"project_id":pid,"direction_adoption.revision":review["decision_revision"]}),1)
        await self.request("POST","/guided/strategic-planning/session/adopt",{"session_id":self.sid,"revision":review["decision_revision"],"confirmed":True})
        await self.request("POST","/guided/strategic-planning/session-plan",{"session_id":self.sid})
        for _ in range(50):
            plan=await self.db.sp_plans.find_one({"project_id":pid})
            if plan.get("final_status") in {"Draft","Failed"}:break
            await asyncio.sleep(.02)
        self.assertEqual(plan["final_status"],"Draft",str(plan))
        context=self.f.AI_CONTEXTS[-1]["context"]
        self.assertNotIn("million",context);self.assertNotIn("Former mentors",context)
        self.assertIn("Help 1,000",context)
        await self.request("POST","/guided/strategic-planning/final-plan/approve",{"session_id":self.sid})
        await self.request("POST","/guided/strategic-planning/final-plan/approve",{"session_id":self.sid})
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({}),1)
        event=await self.db.workflow_email_deliveries.find_one({});self.assertEqual(event["status"],"captured")
        await self.request("POST","/guided/strategic-planning/send-final-plan",{"session_id":self.sid})
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({}),4)
    async def test_fundraising_intro_save_resume_paid_setup_and_multiple_audiences(self):
        await self.launch("board-fundraising-game","intro")
        from current_workflow_fixtures import fundraising_answers
        value=fundraising_answers();second=copy.deepcopy(value["audiences"]["businesses"][0]);second["id"]="second-business";value["audiences"]["businesses"].append(second)
        await self.request("PUT","/game/free/audiences",value)
        loaded=await self.request("GET","/game/free");self.assertEqual(loaded["response"]["audiences"],value["audiences"])
        await self.request("PUT","/game/free/audiences",{**value,"submit":True})
        await self.request("POST","/payments/game-checkout",{"origin_url":"http://test"})
        primary=await self.request("POST","/game/self-play",expected=201)
        record=await self.db.game_board_members.find_one({"member_id":primary["member_id"]});self.assertEqual(record["game_version"],6)
        response=await self.request("GET","/game/play/"+primary["token"]+"/audience-response")
        self.assertTrue(response["response"]["completed"]);self.assertEqual(response["configuration"],fg.configuration())
        await self.request("POST","/game/board-members",{"full_name":"Sample B","email":"b@example.test"},409)
        await self.db.game_nights.insert_one({"user_id":self.user,"meeting_date":"2026-11-15","start_time":"18:00","funding_deadline":"2027-01-01"})
        await self.request("POST","/game/situation/complete")
        board=await self.request("POST","/game/board-members",{"full_name":"Sample B","email":"b@example.test"},201)
        self.assertEqual((await self.db.game_board_members.find_one({"member_id":board["board_member"]["member_id"]}))["game_version"],6)
    async def test_fundraising_group_adoption_identity_final_freeze_delivery_and_retry(self):
        await self.launch("board-fundraising-game")
        session=await self.request("GET","/game/group/session");token=session["session"]["token"]
        self.assertEqual(len(session["audience_review"]["proposals"]),12)
        await self.request("POST","/game/group/start")
        async def action(**payload):
            state=await self.request("GET","/game/group/session")
            return await self.request("POST","/game/group/audience/action",{"revision":state["audience_review"]["revision"],**payload})
        first=session["audience_review"]["proposals"][0]
        for index,p in enumerate(session["audience_review"]["proposals"]):await action(action="decision",proposal_id=p["id"],status="adopted" if index==0 else "rejected",strategy=p["strategy"])
        await action(action="summary")
        state=await self.request("GET","/game/group/session");review=state["audience_review"]
        self.assertEqual(len(review["summary"]["audiences"]),1);self.assertFalse(review["summary"]["commitments"])
        await action(action="adopt",confirmed=True,summary_revision=review["summary"]["revision"])
        person=await self.db.game_board_members.find_one({"user_id":self.user,"is_primary":False})
        identity={"slot_id":person["token"],"device_id":"test-device"}
        await self.request("POST",f"/game/group/play/{token}/acknowledge",{**identity,"revision":review["summary"]["revision"],"confirmed":True},403)
        await self.request("POST",f"/game/group/play/{token}/join",identity)
        await self.request("POST",f"/game/group/play/{token}/acknowledge",{**identity,"revision":review["summary"]["revision"],"confirmed":True})
        await action(action="document")
        state=await self.request("GET","/game/group/session");strategy=state["audience_review"]["strategy"]
        self.assertEqual(len(strategy["agreed_audiences"]),1)
        body={"sections":strategy["document_sections"],"source_revision":strategy["source_revision"],"confirmed":True}
        result=await self.request("POST","/game/group/audience/document",body)
        self.assertTrue(all(d["status"]=="captured" for d in result["delivery"]))
        await self.request("POST","/game/group/audience/document",body)
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({}),4)
        await self.request("POST","/game/group/audience/retry-delivery")
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({}),4)
        self.assertEqual((await self.db.game_strategies.find_one({"strategy_id":strategy["strategy_id"]}))["status"],"adopted")
        pdf=await self.client.get("/api/game/group/audience/download",headers=self.headers);self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b"%PDF"))
    async def test_unauthorized_admin_launch_and_cross_organization_personal_links(self):
        r=await self.client.post("/api/admin/dashboard-preview/strategic-planning");self.assertEqual(r.status_code,401)
        await self.launch("strategic-planning")
        await self.request("POST","/guided/strategic-planning/session/acknowledge/not-a-token",{"revision":"x","confirmed":True,"accept_responsibilities":True},404)
    async def test_existing_game_records_are_not_migrated(self):
        await self.launch("board-fundraising-game")
        await self.db.game_profiles.update_one({"user_id":self.user},{"$unset":{"workflow_version":""}})
        person=await self.db.game_board_members.find_one({"user_id":self.user,"is_primary":True})
        await self.db.game_board_members.update_one({"member_id":person["member_id"]},{"$set":{"game_version":5}})
        before=await self.db.game_board_members.find_one({"member_id":person["member_id"]})
        await self.request("POST","/game/self-play",expected=201)
        self.assertEqual(await self.db.game_board_members.find_one({"member_id":person["member_id"]}),before)

if __name__=="__main__":unittest.main()
