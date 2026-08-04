import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


# Validates that the single UI-submitted assessment persisted with all required fields/metadata.
def test_single_e2e_submission_persisted_with_full_answers():
    load_dotenv(Path("/app/backend/.env"))
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    assert mongo_url, "MONGO_URL is missing"
    assert db_name, "DB_NAME is missing"

    client = MongoClient(mongo_url)
    db = client[db_name]

    record = db.board_assessments.find_one(
        {"assessment_number": "NBB-20260804-8D94C3"},
        sort=[("_id", -1)],
    )

    assert record is not None, "Expected E2E assessment record not found in MongoDB"

    assert record["organization_name"] == "TEST_E2E Community Impact Org"
    assert record["email"] == "qa.nonprofit.board+e2e@example.org"
    assert record["phone"] == "+1 415 555 0199"
    assert record["assessment_number"].startswith("NBB-")
    assert record["status"] == "New Board Assessment"
    assert isinstance(record["submitted_at"], str) and record["submitted_at"].endswith("+00:00")

    required_answers = [
        "name",
        "email",
        "phone",
        "organization_name",
        "mission",
        "city",
        "state_region",
        "country",
        "annual_budget",
        "most_important_board_result",
        "bylaws_board_size",
        "current_board_size",
        "active_board_members",
        "inactive_board_members",
        "present_board_condition",
        "board_type",
        "commitment_conversations",
        "willing_to_allow_step_down",
        "bylaw_clarity",
        "new_board_members_needed",
        "recruitment_timeline",
        "areas_carried_alone",
        "missing_skills_networks",
        "expected_new_member_benefit",
        "people_already_identified",
        "benefits_of_joining",
        "previous_recruitment_experience",
        "present_fundraising_involvement",
        "board_support_areas",
        "written_fundraising_strategy",
        "individual_responsibilities",
        "board_participation_in_planning",
        "missing_fundraising_elements",
        "desired_result",
        "support_required",
        "confirmation_accepted",
    ]

    for field in required_answers:
        assert field in record, f"Missing field in Mongo record: {field}"
        if isinstance(record[field], list):
            assert len(record[field]) > 0, f"Field should not be empty list: {field}"
        elif isinstance(record[field], bool):
            assert record[field] is True, f"Expected True for boolean field: {field}"
        else:
            assert str(record[field]).strip() != "", f"Field should not be empty: {field}"

    assert record.get("owner_email_status") == "Failed"
    assert "Missing RESEND_API_KEY" in str(record.get("owner_email_error", ""))
