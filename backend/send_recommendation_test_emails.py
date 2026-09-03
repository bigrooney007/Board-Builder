"""One-off: send exactly FOUR personalized recommendation TEST emails to the admin. No DB leads created."""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from recommendation_email_service import generate_recommendation_email, deliver_email  # noqa: E402

TEST_LEADS = [
    {"recommended_pathway": "reactivation", "name": "TEST Sarah", "organization": "TEST — Riverside Youth Alliance",
     "board_count": "8", "board_situation": "We have 8 board members on paper but only 3 consistently show up. Several haven't responded to emails in months and honestly I don't know who still wants to serve. I'm doing almost everything myself.",
     "diagnostic_answers": {"has_board": "Yes", "active_participation": "No", "right_people": "Yes", "fundraising_working": "No"}},
    {"recommended_pathway": "recruitment", "name": "TEST Marcus", "organization": "TEST — Second Chance Reentry Project",
     "board_count": "3", "board_situation": "The three of us who started this are still the whole board. We've grown to serving 200 people a year but we have no one with finance, legal or fundraising experience around the table, and no real connections to funders.",
     "diagnostic_answers": {"has_board": "Yes", "active_participation": "Yes", "right_people": "No", "fundraising_working": "No"}},
    {"recommended_pathway": "activation", "name": "TEST Angela", "organization": "TEST — Harvest Table Food Network",
     "board_count": "7", "board_situation": "Our 7 board members attend nearly every meeting and genuinely care. They give good input on programs. But when it comes to fundraising, it all falls on me — nobody on the board raises money or opens doors to donors.",
     "diagnostic_answers": {"has_board": "Yes", "active_participation": "Yes", "right_people": "Yes", "fundraising_working": "No"}},
    {"recommended_pathway": "complete_transformation", "name": "TEST David", "organization": "TEST — Bright Path Learning Center",
     "board_count": "5", "board_situation": "Two of our five board members have quietly disappeared, the ones who remain aren't the skill set we need anymore, and no one has ever helped with fundraising. It feels like the whole board needs to be rebuilt from the ground up.",
     "diagnostic_answers": {"has_board": "Yes", "active_participation": "Some are, some are not", "right_people": "No", "fundraising_working": "No"}},
]


async def main():
    admin = os.environ["ADMIN_EMAIL"].strip('"')
    for lead in TEST_LEADS:
        email = await generate_recommendation_email(lead)
        subject = f"TEST — {email['subject']}"
        deliver_email(admin, subject, email["body"])
        print(f"SENT [{lead['recommended_pathway']}] -> {admin} | {subject}")


asyncio.run(main())
