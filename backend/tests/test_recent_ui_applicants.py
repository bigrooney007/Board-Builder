import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv(Path("/app/backend/.env"))


# Verifies latest UI applicant submissions have expected persistence metadata and email-sync statuses.
def test_recent_ui_us_uk_applicants_have_status_and_metadata():
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    assert mongo_url and db_name

    client = MongoClient(mongo_url)
    db = client[db_name]
    try:
        us = db.board_applicants.find_one(
            {"email": {"$regex": r"^qa\.ui\.us\..*@nonprofitboardbuilder\.com$"}},
            sort=[("updated_at", -1)],
            projection={"_id": 0},
        )
        uk = db.board_applicants.find_one(
            {"email": {"$regex": r"^qa\.ui\.uk\..*@nonprofitboardbuilder\.com$"}},
            sort=[("updated_at", -1)],
            projection={"_id": 0},
        )

        assert us is not None
        assert uk is not None

        for item in (us, uk):
            assert item["source_page"] == "/join-a-board"
            assert item["status"] in {
                "New Applicant",
                "Active",
                "Under Review",
                "Contacted",
                "Presented to Nonprofit",
                "Interviewing",
                "Placed on Board",
                "Paused",
                "Withdrawn",
            }
            assert isinstance(item.get("consent_at"), str) and item.get("consent_at")
            assert isinstance(item.get("created_at"), str) and item.get("created_at")
            assert isinstance(item.get("updated_at"), str) and item.get("updated_at")
            assert item.get("confirmation_email_status") in {"Sent", "Failed"}
            assert item.get("resend_segment_status") in {"Synced", "Failed", "Pending"}

        assert uk["country"] == "United Kingdom"
    finally:
        client.close()
