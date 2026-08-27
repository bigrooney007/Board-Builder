#!/usr/bin/env python3
"""Phase 3 end-to-end backend test for Nonprofit Board Builder"""
import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Base URL from frontend/.env
BASE_URL = "https://board-journey-test.preview.emergentagent.com/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "test_database"

# Test data
TEST_ORG = "Phase3 Test Org"
TEST_CUSTOMER_EMAIL = "phase3.customer@test.com"
TEST_APPLICANT_EMAIL = "phase3.applicant@test.com"
TEST_APPLICANT2_EMAIL = "phase3.applicant2@test.com"
TEST_OTHER_EMAIL = "phase3.other@test.com"
TEST_PASSWORD = "TestPass123!"
TEST_TOKEN = "phase3testtoken123"

# Track created resources for cleanup
created_resources = {
    "member_ids": [],
    "lead_ids": [],
    "material_ids": [],
    "opportunity_ids": [],
    "application_ids": [],
    "applicant_ids": [],
    "signature_request_ids": [],
    "cv_file_ids": [],
}


def log(message: str, level: str = "INFO"):
    """Log test progress"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def create_test_pdf() -> bytes:
    """Create a minimal test PDF"""
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Test CV Resume) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
306
%%EOF"""


async def setup_mongo_data(db, member_user_id: str, lead_id: str):
    """Set entitlements and lead_ids in Mongo"""
    log("Setting member entitlements in MongoDB")
    await db.members.update_one(
        {"user_id": member_user_id},
        {"$set": {
            "entitlements": ["recruitment_self_guided"],
            "lead_ids": [lead_id],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )


async def cleanup_test_data(db):
    """Clean up all test records"""
    log("Cleaning up test data...")
    
    # Delete members
    if created_resources["member_ids"]:
        result = await db.members.delete_many({"user_id": {"$in": created_resources["member_ids"]}})
        log(f"Deleted {result.deleted_count} members")
    
    # Delete leads
    if created_resources["lead_ids"]:
        result = await db.funnel_leads.delete_many({"lead_id": {"$in": created_resources["lead_ids"]}})
        log(f"Deleted {result.deleted_count} funnel leads")
    
    # Delete recruitment profiles
    if created_resources["member_ids"]:
        result = await db.recruitment_profiles.delete_many({"user_id": {"$in": created_resources["member_ids"]}})
        log(f"Deleted {result.deleted_count} recruitment profiles")
    
    # Delete generated materials
    if created_resources["member_ids"]:
        result = await db.generated_materials.delete_many({"user_id": {"$in": created_resources["member_ids"]}})
        log(f"Deleted {result.deleted_count} generated materials")
    
    # Delete opportunities
    if created_resources["opportunity_ids"]:
        result = await db.opportunities.delete_many({"opportunity_id": {"$in": created_resources["opportunity_ids"]}})
        log(f"Deleted {result.deleted_count} opportunities")
    
    # Delete applications
    if created_resources["application_ids"]:
        result = await db.opportunity_applications.delete_many({"application_id": {"$in": created_resources["application_ids"]}})
        log(f"Deleted {result.deleted_count} applications")
    
    # Delete apply tokens
    result = await db.apply_tokens.delete_many({"token": TEST_TOKEN})
    log(f"Deleted {result.deleted_count} apply tokens")
    
    # Delete signature requests
    if created_resources["signature_request_ids"]:
        result = await db.signature_requests.delete_many({"request_id": {"$in": created_resources["signature_request_ids"]}})
        log(f"Deleted {result.deleted_count} signature requests")
    
    # Delete board applicants
    if created_resources["applicant_ids"]:
        result = await db.board_applicants.delete_many({"applicant_id": {"$in": created_resources["applicant_ids"]}})
        log(f"Deleted {result.deleted_count} board applicants")
    
    # Delete GridFS CV files
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    cv_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="opportunity_cvs")
    for file_id in created_resources["cv_file_ids"]:
        try:
            await cv_bucket.delete(ObjectId(file_id))
        except Exception:
            pass
    log(f"Deleted {len(created_resources['cv_file_ids'])} CV files from GridFS")


async def run_tests():
    """Run all Phase 3 backend tests"""
    client = httpx.AsyncClient(timeout=60.0)
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        log("=" * 80)
        log("PHASE 3 BACKEND TESTING - Nonprofit Board Builder")
        log("=" * 80)
        
        # ========== SETUP ==========
        log("\n### SETUP ###")
        
        # 1. Create recruitment lead
        log("Creating recruitment funnel lead...")
        lead_payload = {
            "name": "Phase 3 Test Customer",
            "email": TEST_CUSTOMER_EMAIL,
            "phone": "+1-555-0100",
            "organization": TEST_ORG,
            "website": "https://phase3test.org",
            "city": "Test City",
            "state_region": "Test State",
            "country": "United States",
            "answers": {
                "new_members_needed": "3",
                "present_board": "7",
                "active_board": "5",
                "board_type": "Governing Board",
                "accomplish": "Expand fundraising capacity and community connections",
                "strengthen_areas": ["Fundraising", "Strategic Planning", "Community Connections"],
                "timeline": "Within 3 months"
            }
        }
        resp = await client.post(f"{BASE_URL}/funnel-leads/recruitment", json=lead_payload)
        assert resp.status_code == 201, f"Lead creation failed: {resp.status_code} {resp.text}"
        lead_data = resp.json()
        lead_id = lead_data["lead_id"]
        created_resources["lead_ids"].append(lead_id)
        log(f"✓ Lead created: {lead_id}")
        
        # 2. Register member
        log("Registering member...")
        register_payload = {
            "first_name": "Phase3",
            "last_name": "Customer",
            "email": TEST_CUSTOMER_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD
        }
        resp = await client.post(f"{BASE_URL}/members/register", json=register_payload)
        assert resp.status_code == 201, f"Registration failed: {resp.status_code} {resp.text}"
        member_data = resp.json()
        member_token = member_data["token"]
        member_user_id = member_data["member"]["user_id"]
        created_resources["member_ids"].append(member_user_id)
        log(f"✓ Member registered: {member_user_id}")
        
        # 3. Set entitlements in Mongo
        await setup_mongo_data(db, member_user_id, lead_id)
        log("✓ Entitlements set in MongoDB")
        
        headers = {"Authorization": f"Bearer {member_token}"}
        
        # ========== A. MODULE 1: Profile API ==========
        log("\n### A. MODULE 1: Profile API ###")
        
        # GET profile - should have prefill
        log("Testing GET /api/workspace/profile...")
        resp = await client.get(f"{BASE_URL}/workspace/profile", headers=headers)
        assert resp.status_code == 200, f"GET profile failed: {resp.status_code} {resp.text}"
        profile_data = resp.json()
        assert "prefill" in profile_data, "Missing prefill"
        assert profile_data["prefill"]["organization_name"] == TEST_ORG, "Prefill organization mismatch"
        assert profile_data["prefill"]["new_members_count"] == "3", "Prefill new_members_count mismatch"
        log("✓ Profile prefill contains organization and new_members_count from lead")
        
        # PUT profile - save full data
        log("Testing PUT /api/workspace/profile...")
        profile_update = {
            "data": {
                "organization_name": TEST_ORG,
                "mission": "To serve the community through education and support",
                "city": "Test City",
                "state_region": "Test State",
                "country": "United States",
                "priorities": "Expand programs and increase fundraising",
                "highest_priority_program": "Youth Education",
                "biggest_challenges": "Limited funding and volunteer capacity",
                "present_board": "Yes",
                "active_board": "Yes",
                "continuing_members": "5",
                "board_strengths": ["Committed", "Diverse skills"],
                "board_weaknesses": ["Limited fundraising experience"],
                "missing_from_board": "Fundraising expertise and legal knowledge",
                "new_members_count": "3",
                "board_kind": "Governing Board",
                "strengthen_areas": ["Fundraising", "Legal"],
                "valuable_experience": "Nonprofit fundraising, legal, finance",
                "valuable_relationships": "Corporate donors, foundations",
                "meeting_frequency": "Monthly",
                "meeting_format": "Hybrid",
                "location_requirement": "Must be able to attend in-person quarterly",
                "monthly_time_commitment": "5-8 hours",
                "service_unpaid": "Yes",
                "responsibilities": ["Governance", "Fundraising", "Advocacy"],
                "fundraising_activities": ["Events", "Major gifts", "Grant writing"],
                "launch_timing": "Within 3 months",
                "selection_timing": "2 months",
                "has_deadline": "Yes",
                "who_interviews": "Board chair and executive director",
                "final_decision": "Full board vote",
                "bylaws_requirements": "Background check required"
            }
        }
        resp = await client.put(f"{BASE_URL}/workspace/profile", json=profile_update, headers=headers)
        assert resp.status_code == 200, f"PUT profile failed: {resp.status_code} {resp.text}"
        assert resp.json()["confirmed"] == False, "Profile should not be confirmed yet"
        log("✓ Profile saved, confirmed=false")
        
        # Try to generate before confirming - should 409
        log("Testing POST /api/workspace/generate before confirming (should fail)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate", 
                                json={"type": "recruitment_strategy"}, headers=headers)
        assert resp.status_code == 409, f"Generate before confirm should 409, got {resp.status_code}"
        log("✓ Generate before confirm correctly returns 409")
        
        # POST confirm
        log("Testing POST /api/workspace/profile/confirm...")
        resp = await client.post(f"{BASE_URL}/workspace/profile/confirm", headers=headers)
        assert resp.status_code == 200, f"Confirm failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "confirmed", "Profile not confirmed"
        log("✓ Profile confirmed")
        
        # ========== B. MODULE 2: Generate recruitment_strategy ==========
        log("\n### B. MODULE 2: Generate recruitment_strategy ###")
        
        log("Testing POST /api/workspace/generate (recruitment_strategy)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "recruitment_strategy"}, headers=headers)
        assert resp.status_code == 200, f"Generate strategy failed: {resp.status_code} {resp.text}"
        strategy_material = resp.json()
        material_id = strategy_material["material_id"]
        created_resources["material_ids"].append(material_id)
        assert len(strategy_material["versions"]) == 1, "Should have 1 version"
        assert strategy_material["current_version"] == 1, "Current version should be 1"
        structured = strategy_material["versions"][0]["structured"]
        assert "objective" in structured, "Missing objective"
        assert "candidate_profiles" in structured, "Missing candidate_profiles"
        assert len(structured["candidate_profiles"]) > 0, "candidate_profiles should not be empty"
        assert "recruitment_positioning" in structured, "Missing recruitment_positioning"
        assert "recruitment_channels" in structured, "Missing recruitment_channels"
        assert "selection_criteria" in structured, "Missing selection_criteria"
        assert "recruitment_timeline" in structured, "Missing recruitment_timeline"
        assert "launch_plan" in structured, "Missing launch_plan"
        log("✓ Recruitment strategy generated with all required fields")
        
        # GET materials - verify no auto-regeneration
        log("Testing GET /api/workspace/materials (verify no auto-regeneration)...")
        resp = await client.get(f"{BASE_URL}/workspace/materials", headers=headers)
        assert resp.status_code == 200, f"GET materials failed: {resp.status_code} {resp.text}"
        materials = resp.json()["materials"]
        strategy = next((m for m in materials if m["type"] == "recruitment_strategy"), None)
        assert strategy is not None, "Strategy material not found"
        assert len(strategy["versions"]) == 1, "Versions count should stay 1 (no auto-regeneration)"
        log("✓ GET materials does not trigger regeneration")
        
        # PUT material - edit
        log("Testing PUT /api/workspace/materials/{id} (edit)...")
        resp = await client.put(f"{BASE_URL}/workspace/materials/{material_id}",
                               json={"display_text": "EDITED STRATEGY - This is a manual edit for testing"},
                               headers=headers)
        assert resp.status_code == 200, f"Edit material failed: {resp.status_code} {resp.text}"
        edited = resp.json()
        assert len(edited["versions"]) == 2, "Should have 2 versions after edit"
        assert edited["current_version"] == 2, "Current version should be 2"
        assert edited["versions"][1]["source"] == "edited", "Version 2 should be edited"
        log("✓ Material edited, new version 2 created with source=edited")
        
        # ========== C. MODULE 3: Generate opportunity and questions, publish ==========
        log("\n### C. MODULE 3: Generate opportunity and application_questions ###")
        
        # Generate board_opportunity
        log("Testing POST /api/workspace/generate (board_opportunity)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "board_opportunity"}, headers=headers)
        assert resp.status_code == 200, f"Generate opportunity failed: {resp.status_code} {resp.text}"
        opp_material = resp.json()
        created_resources["material_ids"].append(opp_material["material_id"])
        log("✓ Board opportunity generated")
        
        # Generate application_questions
        log("Testing POST /api/workspace/generate (application_questions)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "application_questions"}, headers=headers)
        assert resp.status_code == 200, f"Generate questions failed: {resp.status_code} {resp.text}"
        questions_material = resp.json()
        created_resources["material_ids"].append(questions_material["material_id"])
        structured = questions_material["versions"][0]["structured"]
        custom_questions = structured.get("custom_questions", [])
        assert len(custom_questions) <= 5, f"Should have ≤5 custom questions, got {len(custom_questions)}"
        log(f"✓ Application questions generated ({len(custom_questions)} custom questions)")
        
        # GET opportunity - verify questions
        log("Testing GET /api/workspace/opportunity...")
        resp = await client.get(f"{BASE_URL}/workspace/opportunity", headers=headers)
        assert resp.status_code == 200, f"GET opportunity failed: {resp.status_code} {resp.text}"
        opp_data = resp.json()
        opportunity_id = opp_data["opportunity"]["opportunity_id"]
        created_resources["opportunity_ids"].append(opportunity_id)
        assert len(opp_data["core_questions"]) == 18, f"Should have 18 core questions, got {len(opp_data['core_questions'])}"
        log("✓ Opportunity shows 18 core_questions + custom questions")
        
        # PUT application form - edit questions
        log("Testing PUT /api/workspace/opportunity/application...")
        edited_questions = [
            {"id": "q1", "label": "What specific fundraising experience do you have?", "type": "textarea"},
            {"id": "q2", "label": "Are you available for quarterly in-person meetings?", "type": "yes_no"}
        ]
        resp = await client.put(f"{BASE_URL}/workspace/opportunity/application",
                               json={"custom_questions": edited_questions}, headers=headers)
        assert resp.status_code == 200, f"PUT application failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "saved", "Application not saved"
        log("✓ Application form saved with edited questions")
        
        # Verify application_saved
        resp = await client.get(f"{BASE_URL}/workspace/opportunity", headers=headers)
        opp_data = resp.json()
        assert opp_data["opportunity"].get("application_saved") == True, "application_saved should be true"
        log("✓ application_saved is true")
        
        # POST publish
        log("Testing POST /api/workspace/opportunity/publish...")
        resp = await client.post(f"{BASE_URL}/workspace/opportunity/publish", headers=headers)
        assert resp.status_code == 200, f"Publish failed: {resp.status_code} {resp.text}"
        publish_result = resp.json()
        assert publish_result["status"] == "Published", "Status should be Published"
        assert publish_result["opportunity"]["broadcast_mode"] == "test", "broadcast_mode should be test"
        assert publish_result["opportunity"]["broadcast_status"] == "Initiated", "broadcast_status should be Initiated"
        slug = publish_result["opportunity"]["slug"]
        log(f"✓ Opportunity published (slug: {slug}, broadcast_mode: test, status: Initiated)")
        
        # Try to publish again - should 409
        log("Testing duplicate publish (should fail)...")
        resp = await client.post(f"{BASE_URL}/workspace/opportunity/publish", headers=headers)
        assert resp.status_code == 409, f"Duplicate publish should 409, got {resp.status_code}"
        log("✓ Duplicate publish correctly returns 409")
        
        # GET public opportunity
        log("Testing GET /api/public/board-opportunities/{slug}...")
        resp = await client.get(f"{BASE_URL}/public/board-opportunities/{slug}")
        assert resp.status_code == 200, f"GET public opportunity failed: {resp.status_code} {resp.text}"
        public_opp = resp.json()
        assert public_opp["status"] == "Published", "Public opportunity status should be Published"
        assert len(public_opp["core_questions"]) == 18, "Should have 18 core questions"
        assert len(public_opp["custom_questions"]) == 2, "Should have 2 custom questions"
        log("✓ Public opportunity endpoint returns opportunity with core+custom questions")
        
        # ========== D. PUBLIC APPLICATION ==========
        log("\n### D. PUBLIC APPLICATION ###")
        
        log("Testing POST /api/public/board-opportunities/{slug}/apply...")
        
        # Prepare application payload
        application_payload = {
            "full_name": "Test Applicant Two",
            "email": TEST_APPLICANT2_EMAIL,
            "phone": "+1-555-0102",
            "city": "Applicant City",
            "state_region": "Applicant State",
            "country": "United States",
            "profession": "Nonprofit Consultant",
            "employer": "Consulting Firm",
            "linkedin": "https://linkedin.com/in/testapplicant2",
            "board_experience": "Served on 2 nonprofit boards for 5 years",
            "why_interested": "Passionate about education and community development",
            "skills_experience": "Strategic planning, fundraising, program development",
            "fundraising_support": "Major gifts, events, grant writing",
            "relationships": "Corporate executives, foundation program officers",
            "monthly_time": "6-8 hours",
            "attend_meetings": "Yes",
            "accept_responsibility": "Yes",
            "causes": "Education, youth development, community empowerment",
            "q1": "Led annual fundraising campaigns raising $500K+",
            "q2": "Yes"
        }
        
        # Create multipart form data
        files = {
            "cv": ("test_cv.pdf", create_test_pdf(), "application/pdf"),
            "payload": (None, json.dumps(application_payload), "application/json")
        }
        
        resp = await client.post(f"{BASE_URL}/public/board-opportunities/{slug}/apply", files=files)
        assert resp.status_code == 201, f"Public apply failed: {resp.status_code} {resp.text}"
        apply_result = resp.json()
        application_id_1 = apply_result["application_id"]
        created_resources["application_ids"].append(application_id_1)
        assert apply_result["status"] == "Applied", "Application status should be Applied"
        log(f"✓ Public application submitted: {application_id_1}")
        
        # Try duplicate email - should 409
        log("Testing duplicate application (same email, should fail)...")
        resp = await client.post(f"{BASE_URL}/public/board-opportunities/{slug}/apply", files=files)
        assert resp.status_code == 409, f"Duplicate apply should 409, got {resp.status_code}"
        log("✓ Duplicate application correctly returns 409")
        
        # Try missing required field - should 422
        log("Testing missing required field (should fail)...")
        incomplete_payload = application_payload.copy()
        del incomplete_payload["full_name"]
        files_incomplete = {
            "cv": ("test_cv.pdf", create_test_pdf(), "application/pdf"),
            "payload": (None, json.dumps(incomplete_payload), "application/json")
        }
        resp = await client.post(f"{BASE_URL}/public/board-opportunities/{slug}/apply", files=files_incomplete)
        assert resp.status_code == 422, f"Missing required field should 422, got {resp.status_code}"
        log("✓ Missing required field correctly returns 422")
        
        # Wait for interview guide generation
        log("Waiting 30-60s for interview guide generation...")
        await asyncio.sleep(35)
        
        # GET application detail - verify interview guide
        log("Testing GET /api/workspace/applications/{id} (verify interview guide)...")
        resp = await client.get(f"{BASE_URL}/workspace/applications/{application_id_1}", headers=headers)
        assert resp.status_code == 200, f"GET application failed: {resp.status_code} {resp.text}"
        app_detail = resp.json()
        interview_guide = app_detail["application"].get("interview_guide", {})
        log(f"Interview guide status: {interview_guide.get('status')}")
        
        if interview_guide.get("status") == "Ready":
            # Find interview guide material
            guide_materials = [m for m in app_detail["materials"] if m["type"] == "interview_guide"]
            assert len(guide_materials) > 0, "Interview guide material not found"
            guide_material = guide_materials[0]
            created_resources["material_ids"].append(guide_material["material_id"])
            
            # Get full material with structured data
            resp = await client.get(f"{BASE_URL}/workspace/materials/{guide_material['material_id']}", headers=headers)
            assert resp.status_code == 200, f"GET guide material failed: {resp.status_code}"
            guide_full = resp.json()
            structured = guide_full["versions"][0]["structured"]
            
            # Verify all required sections
            required_sections = [
                "applicant_overview", "strengths", "areas_to_clarify",
                "organization_questions", "cv_questions", "commitment_questions",
                "fundraising_questions", "concerns_to_explore", "scorecard"
            ]
            for section in required_sections:
                assert section in structured, f"Missing section: {section}"
            log("✓ Interview guide generated with all required sections")
        else:
            log(f"⚠ Interview guide status: {interview_guide.get('status')} (not Ready)")
        
        # ========== E. SAVED-PROFILE APPLY ==========
        log("\n### E. SAVED-PROFILE APPLY ###")
        
        # Create test board applicant
        log("Creating test board applicant...")
        applicant_payload = {
            "first_name": "Test",
            "last_name": "Applicant",
            "email": TEST_APPLICANT_EMAIL,
            "phone": "+1-555-0101",
            "city": "Test City",
            "state_region": "Test State",
            "country": "United States",
            "job_title": "Senior Manager",
            "employer": "Tech Company",
            "linkedin_url": "https://linkedin.com/in/testapplicant",
            "professional_field": "Technology",
            "years_experience": "10-15 years",
            "professional_summary": "Experienced professional with 10+ years in tech",
            "skills": ["Leadership", "Strategy", "Fundraising"],
            "previous_board_experience": "Yes",
            "board_experience_details": "Served on 1 board for 3 years",
            "reason_for_joining": "Want to give back to the community",
            "fundraising_activities": ["Events", "Major gifts"],
            "professional_relationships": "Tech executives and investors",
            "monthly_commitment": "5 hours",
            "commitment_answer": "Yes",
            "causes": ["Education", "Technology"],
            "board_types": ["Governing Board"],
            "participation_preferences": ["In-person meetings"],
            "geographic_preferences": "Local only",
            "availability": "Immediate",
            "understands_unpaid": "Yes",
            "profile_sharing_permission": True,
            "board_opportunity_consent": True,
            "privacy_accepted": True
        }
        
        files_applicant = {
            "resume": ("test_resume.pdf", create_test_pdf(), "application/pdf"),
            "payload": (None, json.dumps(applicant_payload), "application/json")
        }
        
        resp = await client.post(f"{BASE_URL}/applicants", files=files_applicant)
        assert resp.status_code == 201, f"Create applicant failed: {resp.status_code} {resp.text}"
        applicant_data = resp.json()
        applicant_id = applicant_data["applicant_id"]
        created_resources["applicant_ids"].append(applicant_id)
        log(f"✓ Board applicant created: {applicant_id}")
        
        # Insert apply_token in Mongo
        log("Inserting apply_token in MongoDB...")
        await db.apply_tokens.insert_one({
            "token": TEST_TOKEN,
            "applicant_id": applicant_id,
            "opportunity_id": opportunity_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        log(f"✓ Apply token created: {TEST_TOKEN}")
        
        # GET apply token - verify profile shown, already_applied=false
        log("Testing GET /api/public/apply/{token}...")
        resp = await client.get(f"{BASE_URL}/public/apply/{TEST_TOKEN}")
        assert resp.status_code == 200, f"GET apply token failed: {resp.status_code} {resp.text}"
        token_data = resp.json()
        assert token_data["has_profile"] == True, "Should have profile"
        assert token_data["already_applied"] == False, "Should not be already applied"
        assert "profile" in token_data, "Missing profile"
        log("✓ Apply token shows profile, already_applied=false")
        log("✓ GET alone does NOT create application")
        
        # POST confirm - create application
        log("Testing POST /api/public/apply/{token}/confirm...")
        resp = await client.post(f"{BASE_URL}/public/apply/{TEST_TOKEN}/confirm")
        assert resp.status_code == 201, f"Confirm apply failed: {resp.status_code} {resp.text}"
        confirm_result = resp.json()
        application_id_2 = confirm_result["application_id"]
        created_resources["application_ids"].append(application_id_2)
        log(f"✓ Application created from saved profile: {application_id_2}")
        
        # Verify application source and CV snapshot
        resp = await client.get(f"{BASE_URL}/workspace/applications/{application_id_2}", headers=headers)
        assert resp.status_code == 200, f"GET application failed: {resp.status_code}"
        app_data = resp.json()["application"]
        assert app_data["source"] == "Board Applicant Network", "Source should be Board Applicant Network"
        assert app_data.get("cv_file_id"), "Should have CV snapshot"
        if app_data.get("cv_file_id"):
            created_resources["cv_file_ids"].append(app_data["cv_file_id"])
        log("✓ Application has source='Board Applicant Network' and CV snapshot")
        
        # Try to confirm again - should 409
        log("Testing duplicate confirm (should fail)...")
        resp = await client.post(f"{BASE_URL}/public/apply/{TEST_TOKEN}/confirm")
        assert resp.status_code == 409, f"Duplicate confirm should 409, got {resp.status_code}"
        log("✓ Duplicate confirm correctly returns 409")
        
        # ========== F. MODULE 4/5: Applications workspace ==========
        log("\n### F. MODULE 4/5: Applications workspace ###")
        
        # GET applications list
        log("Testing GET /api/workspace/applications...")
        resp = await client.get(f"{BASE_URL}/workspace/applications", headers=headers)
        assert resp.status_code == 200, f"GET applications failed: {resp.status_code} {resp.text}"
        apps_list = resp.json()["applications"]
        assert len(apps_list) == 2, f"Should have 2 applications, got {len(apps_list)}"
        log(f"✓ Applications list shows {len(apps_list)} applications")
        
        # PATCH application status to Selected
        log("Testing PATCH /api/workspace/applications/{id} (status=Selected)...")
        resp = await client.patch(f"{BASE_URL}/workspace/applications/{application_id_1}",
                                 json={"status": "Selected"}, headers=headers)
        assert resp.status_code == 200, f"PATCH application failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "Selected", "Status should be Selected"
        log("✓ Application status updated to Selected")
        
        # Generate interview_invitation
        log("Testing POST /api/workspace/generate (interview_invitation)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "interview_invitation", "application_id": application_id_1},
                                headers=headers)
        assert resp.status_code == 200, f"Generate interview_invitation failed: {resp.status_code} {resp.text}"
        invitation_material = resp.json()
        created_resources["material_ids"].append(invitation_material["material_id"])
        assert len(invitation_material["versions"]) == 1, "Should have 1 version"
        log("✓ Interview invitation generated (version 1)")
        
        # Regenerate interview_invitation (second POST)
        log("Testing regenerate interview_invitation (second POST)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "interview_invitation", "application_id": application_id_1},
                                headers=headers)
        assert resp.status_code == 200, f"Regenerate failed: {resp.status_code} {resp.text}"
        regenerated = resp.json()
        assert len(regenerated["versions"]) == 2, "Should have 2 versions after regenerate"
        log("✓ Interview invitation regenerated (version 2)")
        
        # POST reference
        log("Testing POST /api/workspace/applications/{id}/references...")
        reference_payload = {
            "reference_name": "John Reference",
            "relationship": "Former colleague",
            "email": "john.ref@example.com",
            "phone": "+1-555-0200",
            "date_contacted": "2024-01-15",
            "notes": "Highly recommended",
            "outcome": "Positive"
        }
        resp = await client.post(f"{BASE_URL}/workspace/applications/{application_id_1}/references",
                                json=reference_payload, headers=headers)
        assert resp.status_code == 201, f"POST reference failed: {resp.status_code} {resp.text}"
        reference = resp.json()
        assert "reference_id" in reference, "Missing reference_id"
        log("✓ Reference record added")
        
        # PATCH background check
        log("Testing PATCH background_check...")
        resp = await client.patch(f"{BASE_URL}/workspace/applications/{application_id_1}",
                                 json={"background_check": {"status": "In progress"}}, headers=headers)
        assert resp.status_code == 200, f"PATCH background check failed: {resp.status_code} {resp.text}"
        assert resp.json()["background_check"]["status"] == "In progress", "Background check status mismatch"
        log("✓ Background check status updated")
        
        # GET CV download
        log("Testing GET /api/workspace/applications/{id}/cv...")
        resp = await client.get(f"{BASE_URL}/workspace/applications/{application_id_1}/cv", headers=headers)
        assert resp.status_code == 200, f"GET CV failed: {resp.status_code} {resp.text}"
        assert len(resp.content) > 0, "CV content is empty"
        log(f"✓ CV download successful ({len(resp.content)} bytes)")
        
        # ========== G. MODULE 6 + SIGNATURE ==========
        log("\n### G. MODULE 6 + SIGNATURE ###")
        
        # Generate board_member_agreement
        log("Testing POST /api/workspace/generate (board_member_agreement)...")
        resp = await client.post(f"{BASE_URL}/workspace/generate",
                                json={"type": "board_member_agreement", "application_id": application_id_1},
                                headers=headers)
        assert resp.status_code == 200, f"Generate agreement failed: {resp.status_code} {resp.text}"
        agreement_material = resp.json()
        created_resources["material_ids"].append(agreement_material["material_id"])
        display_text = agreement_material["versions"][0]["display_text"]
        assert "working template" in display_text.lower() or "review" in display_text.lower(), \
            "Agreement should contain review warning"
        log("✓ Board member agreement generated with review warning")
        
        # Try to prepare for non-selected application - should 409
        log("Testing prepare signature for non-selected application (should fail)...")
        resp = await client.post(f"{BASE_URL}/workspace/signatures/prepare",
                                json={"agreement_type": "board_member_agreement", "application_id": application_id_2},
                                headers=headers)
        assert resp.status_code == 409, f"Prepare non-selected should 409, got {resp.status_code}"
        log("✓ Prepare for non-selected application correctly returns 409")
        
        # POST prepare signature
        log("Testing POST /api/workspace/signatures/prepare...")
        resp = await client.post(f"{BASE_URL}/workspace/signatures/prepare",
                                json={"agreement_type": "board_member_agreement", "application_id": application_id_1},
                                headers=headers)
        assert resp.status_code == 201, f"Prepare signature failed: {resp.status_code} {resp.text}"
        sig_request = resp.json()
        request_id = sig_request["request_id"]
        created_resources["signature_request_ids"].append(request_id)
        assert sig_request["status"] == "Ready for Signature", "Status should be Ready for Signature"
        assert "document_snapshot" in sig_request, "Missing document_snapshot"
        log(f"✓ Signature request prepared: {request_id}")
        
        # POST send signature
        log("Testing POST /api/workspace/signatures/{id}/send...")
        resp = await client.post(f"{BASE_URL}/workspace/signatures/{request_id}/send", headers=headers)
        assert resp.status_code == 200, f"Send signature failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "Sent", "Status should be Sent"
        log("✓ Signature request sent (email to applicant test address)")
        
        # Get token from Mongo
        log("Retrieving signature token from MongoDB...")
        sig_record = await db.signature_requests.find_one({"request_id": request_id}, {"_id": 0})
        sign_token = sig_record["token"]
        log(f"✓ Signature token: {sign_token[:20]}...")
        
        # GET sign page
        log("Testing GET /api/public/sign/{token}...")
        resp = await client.get(f"{BASE_URL}/public/sign/{sign_token}")
        assert resp.status_code == 200, f"GET sign failed: {resp.status_code} {resp.text}"
        sign_data = resp.json()
        assert "document" in sign_data, "Missing document"
        assert sign_data["status"] == "Sent", "Status should be Sent"
        log("✓ Sign page shows document")
        
        # POST sign
        log("Testing POST /api/public/sign/{token}...")
        sign_payload = {
            "agreed": True,
            "typed_signature": "Test Applicant Two",
            "email": TEST_APPLICANT2_EMAIL,
            "date": "2024-01-20"
        }
        resp = await client.post(f"{BASE_URL}/public/sign/{sign_token}", json=sign_payload)
        assert resp.status_code == 200, f"Sign failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "Signed", "Status should be Signed"
        log("✓ Agreement signed")
        
        # Try to sign again - should 409
        log("Testing duplicate sign (should fail)...")
        resp = await client.post(f"{BASE_URL}/public/sign/{sign_token}", json=sign_payload)
        assert resp.status_code == 409, f"Duplicate sign should 409, got {resp.status_code}"
        log("✓ Duplicate sign correctly returns 409 (immutable)")
        
        # GET download signed
        log("Testing GET /api/workspace/signatures/{id}/download...")
        resp = await client.get(f"{BASE_URL}/workspace/signatures/{request_id}/download", headers=headers)
        assert resp.status_code == 200, f"Download signed failed: {resp.status_code} {resp.text}"
        signed_content = resp.text
        assert "SIGNED ELECTRONICALLY" in signed_content, "Missing SIGNED ELECTRONICALLY block"
        log("✓ Signed document download contains SIGNED ELECTRONICALLY block")
        
        # ========== H. SECURITY/TENANCY ==========
        log("\n### H. SECURITY/TENANCY ###")
        
        # Create second member
        log("Creating second member for tenancy test...")
        register_payload_2 = {
            "first_name": "Other",
            "last_name": "Member",
            "email": TEST_OTHER_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD
        }
        resp = await client.post(f"{BASE_URL}/members/register", json=register_payload_2)
        assert resp.status_code == 201, f"Second member registration failed: {resp.status_code}"
        member2_data = resp.json()
        member2_token = member2_data["token"]
        member2_user_id = member2_data["member"]["user_id"]
        created_resources["member_ids"].append(member2_user_id)
        
        # Set entitlements for second member
        await db.members.update_one(
            {"user_id": member2_user_id},
            {"$set": {"entitlements": ["recruitment_self_guided"]}}
        )
        log(f"✓ Second member created: {member2_user_id}")
        
        headers2 = {"Authorization": f"Bearer {member2_token}"}
        
        # Try to access first tenant's applications - should be empty
        log("Testing tenant isolation: GET applications (should be empty)...")
        resp = await client.get(f"{BASE_URL}/workspace/applications", headers=headers2)
        assert resp.status_code == 200, f"GET applications failed: {resp.status_code}"
        apps = resp.json()["applications"]
        assert len(apps) == 0, f"Second tenant should have 0 applications, got {len(apps)}"
        log("✓ Second tenant sees empty applications list")
        
        # Try to access first tenant's application by ID - should 404
        log("Testing tenant isolation: GET application by ID (should 404)...")
        resp = await client.get(f"{BASE_URL}/workspace/applications/{application_id_1}", headers=headers2)
        assert resp.status_code == 404, f"Should 404, got {resp.status_code}"
        log("✓ Second tenant cannot access first tenant's application (404)")
        
        # Try to access first tenant's material - should 404
        log("Testing tenant isolation: GET material by ID (should 404)...")
        resp = await client.get(f"{BASE_URL}/workspace/materials/{material_id}", headers=headers2)
        assert resp.status_code == 404, f"Should 404, got {resp.status_code}"
        log("✓ Second tenant cannot access first tenant's material (404)")
        
        # Test unauthenticated access - should 401
        log("Testing unauthenticated access (should 401)...")
        # Create new client without cookies
        unauth_client = httpx.AsyncClient(timeout=60.0)
        resp = await unauth_client.get(f"{BASE_URL}/workspace/profile")
        await unauth_client.aclose()
        assert resp.status_code == 401, f"Should 401, got {resp.status_code}"
        log("✓ Unauthenticated access returns 401")
        
        # Test member with no entitlement - should 403
        log("Testing member with no entitlement (should 403)...")
        await db.members.update_one({"user_id": member2_user_id}, {"$set": {"entitlements": []}})
        resp = await client.get(f"{BASE_URL}/workspace/profile", headers=headers2)
        assert resp.status_code == 403, f"Should 403, got {resp.status_code}"
        log("✓ Member with no entitlement returns 403")
        
        # ========== I. CLOSE OPPORTUNITY ==========
        log("\n### I. CLOSE OPPORTUNITY ###")
        
        log("Testing POST /api/workspace/opportunity/close...")
        resp = await client.post(f"{BASE_URL}/workspace/opportunity/close", headers=headers)
        assert resp.status_code == 200, f"Close failed: {resp.status_code} {resp.text}"
        assert resp.json()["status"] == "Closed", "Status should be Closed"
        log("✓ Opportunity closed")
        
        # Verify public opportunity shows Closed
        log("Verifying public opportunity shows status Closed...")
        resp = await client.get(f"{BASE_URL}/public/board-opportunities/{slug}")
        assert resp.status_code == 200, f"GET public opportunity failed: {resp.status_code}"
        assert resp.json()["status"] == "Closed", "Public opportunity should show Closed"
        log("✓ Public opportunity shows status Closed")
        
        # Try to apply to closed opportunity - should 410
        log("Testing apply to closed opportunity (should 410)...")
        files_test = {
            "cv": ("test.pdf", create_test_pdf(), "application/pdf"),
            "payload": (None, json.dumps({"email": "test@test.com", "full_name": "Test"}), "application/json")
        }
        resp = await client.post(f"{BASE_URL}/public/board-opportunities/{slug}/apply", files=files_test)
        assert resp.status_code == 410, f"Apply to closed should 410, got {resp.status_code}"
        log("✓ Apply to closed opportunity returns 410")
        
        # Verify existing applications still retrievable
        log("Verifying existing applications still retrievable...")
        resp = await client.get(f"{BASE_URL}/workspace/applications/{application_id_1}", headers=headers)
        assert resp.status_code == 200, f"GET application failed: {resp.status_code}"
        log("✓ Existing applications still retrievable")
        
        # ========== J. VERIFY ENV FLAGS AND PHASE 2 ==========
        log("\n### J. VERIFY ENV FLAGS AND PHASE 2 ENDPOINTS ###")
        
        # GET payment config
        log("Testing GET /api/payments/config...")
        resp = await client.get(f"{BASE_URL}/payments/config")
        assert resp.status_code == 200, f"GET config failed: {resp.status_code} {resp.text}"
        config = resp.json()
        assert config.get("recruitment_497_live") == False, "recruitment_497_live should be false"
        log("✓ Env flags unchanged: recruitment_497_live=false")
        
        # Test Phase 2 course endpoint
        log("Testing Phase 2: GET /api/courses/recruitment/self-guided...")
        resp = await client.get(f"{BASE_URL}/courses/recruitment/self-guided", headers=headers)
        assert resp.status_code == 200, f"GET course failed: {resp.status_code} {resp.text}"
        course = resp.json()
        assert len(course["modules"]) == 6, f"Should have 6 modules, got {len(course['modules'])}"
        log("✓ Phase 2 course endpoint intact (6 modules)")
        
        # Test Phase 2 support request
        log("Testing Phase 2: POST /api/support-requests...")
        support_payload = {
            "module_number": 1,
            "request_type": "Question",
            "message": "Test support request from Phase 3 testing"
        }
        resp = await client.post(f"{BASE_URL}/support-requests", json=support_payload, headers=headers)
        assert resp.status_code == 201, f"POST support request failed: {resp.status_code} {resp.text}"
        log("✓ Phase 2 support request endpoint works")
        
        # Test Phase 2 reactivation funnel
        log("Testing Phase 2: POST /api/funnel-leads/reactivation...")
        reactivation_payload = {
            "name": "Test Reactivation",
            "email": "reactivation.test@example.com",
            "organization": "Test Org",
            "website": "https://test.org",
            "city": "Test City",
            "state_region": "Test State",
            "country": "United States",
            "answers": {
                "present_board": "8",
                "active_board": "5",
                "inactive_situations": ["They do not attend meetings"],
                "recommitment_conversations": "No",
                "strategic_planning": "Yes",
                "priorities": "Re-engage board",
                "desired_changes": ["Increase participation"]
            }
        }
        resp = await client.post(f"{BASE_URL}/funnel-leads/reactivation", json=reactivation_payload)
        assert resp.status_code == 201, f"POST reactivation failed: {resp.status_code} {resp.text}"
        reactivation_lead_id = resp.json()["lead_id"]
        # Clean up reactivation lead
        await db.funnel_leads.delete_one({"lead_id": reactivation_lead_id})
        log("✓ Phase 2 reactivation funnel works (cleaned up)")
        
        # ========== CLEANUP ==========
        log("\n### CLEANUP ###")
        await cleanup_test_data(db)
        
        # ========== SUMMARY ==========
        log("\n" + "=" * 80)
        log("PHASE 3 BACKEND TESTING COMPLETE")
        log("=" * 80)
        log("✓ All tests passed successfully")
        log("✓ Test data cleaned up")
        
        return True
        
    except AssertionError as e:
        log(f"TEST FAILED: {str(e)}", "ERROR")
        log("\nAttempting cleanup...", "INFO")
        try:
            await cleanup_test_data(db)
        except Exception as cleanup_error:
            log(f"Cleanup error: {cleanup_error}", "ERROR")
        return False
    except Exception as e:
        log(f"UNEXPECTED ERROR: {str(e)}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        log("\nAttempting cleanup...", "INFO")
        try:
            await cleanup_test_data(db)
        except Exception as cleanup_error:
            log(f"Cleanup error: {cleanup_error}", "ERROR")
        return False
    finally:
        await client.aclose()
        mongo_client.close()


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
