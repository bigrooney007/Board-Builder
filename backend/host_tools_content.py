"""Default static content for the Board Fundraising Day/Night host tools (no AI)."""

DEFAULT_HOST_TOOLS = {
    "call_script": {
        "page_title": "Call Script",
        "intro": "Use this script to make sure every board member completes their Board Fundraising Game before your meeting. The invitation is already in their inbox.",
        "sections": [
            {
                "key": "script",
                "heading": "Call Script",
                "body": "Hi [Board Member First Name], I wanted to make sure you saw the Board Fundraising Game invitation we sent to your email.\n\nBefore our next board meeting on [Meeting Date], we need every board member to play the game.\n\nIt will walk you through your ideas about who should fund our mission, where we can find them, how we can attract their attention and how we can raise money from them.\n\nYour ideas will be brought into the Board Fundraising Day/Night so we can build the fundraising strategy together.\n\nThe game is already waiting for you in your inbox.\n\nPlease complete it before the meeting.\n\nIf you cannot find the email, let me know and I will resend it.",
            },
        ],
    },
    "facilitation": {
        "page_title": "Board Fundraising Day/Night Facilitation Guide",
        "sections": [
            {
                "key": "before",
                "heading": "Before The Meeting",
                "blocks": [
                    {"kind": "list", "items": [
                        "Confirm that board members have received their Board Fundraising Game invitation.",
                        "Encourage everyone to complete their Individual Game before the meeting.",
                        "Save your meeting details inside the dashboard.",
                        "Make sure the Group Game is ready.",
                        "Have your laptop and screen-sharing or presentation setup ready.",
                    ]},
                ],
            },
            {
                "key": "starting",
                "heading": "Starting The Meeting",
                "blocks": [
                    {"kind": "list", "items": [
                        "Explain that the purpose of the session is to bring the board's fundraising ideas together and decide how the organization will raise money.",
                        "Open the Group Game.",
                        "Explain that the board will review ideas contributed by everyone who played.",
                    ]},
                ],
            },
            {
                "key": "during",
                "heading": "During The Group Game",
                "blocks": [
                    {"kind": "note", "label": "The Rule For Every Screen", "text": "Keep the microphone transcription running. Show every idea without flattening or rewriting it. Discuss the ideas first. As the Board agrees, the Lead User checks every idea that should move forward. If the Board creates better wording or a new idea in the discussion, add that agreed wording before continuing. The checked decisions and transcript work together: the clicks show WHAT the Board adopted; the transcript explains WHY, changes, conditions and delegation."},
                    {"kind": "numbered", "items": [
                        "WHO SHOULD FUND US — Review every proposed individual, business and grantor audience. Check every audience the Board agrees actually fits the mission and fundraising goal.",
                        "WHERE TO FIND THEM — Review the places, networks, relationships and search methods. Check the ones the Board believes it can execute consistently.",
                        "HOW TO ATTRACT THEIR ATTENTION — Review Board ideas and Nonprofit Board Builder recommendations. Adopt the approaches that fit the chosen audiences and the organization's voice.",
                        "FUNDRAISING PROCESS — Agree how each chosen audience moves through Know, Like, Trust, Ask, Follow Up and Stewardship. Preserve any existing process the organization says is already working.",
                        "TEAM — Review the exact people/capacity the strategy needs alongside what each participant already said they are willing to do. Ask each person to confirm, change or decline the role in the room. Check only the roles/capacity the Board agrees on. If nobody can own a required responsibility, leave it as capacity the organization still needs. Say every final delegation aloud for the transcript.",
                        "TECHNOLOGY — Agree on the smallest technology stack the team can actually maintain. Reuse existing tools and free/low-cost tiers before adding unnecessary subscriptions.",
                        "MATERIALS AND CONTENT — Agree on the case for support, audience messages, partnership/grant materials, follow-up templates, evidence, stories and campaign content the chosen strategy actually requires.",
                        "BUDGET — Review what execution genuinely costs. Separate REQUIRED NOW from LATER. Ask what can be done with existing people, tools, templates, free tiers or current subscriptions before approving new spending.",
                        "EXECUTION AND ACCOUNTABILITY — Build a practical 90–120 day sequence: first build capacity and the system, then launch visibility/relationship activity, then move ready prospects into asks, then review results and repeat. Confirm owners, first actions and the Board accountability rhythm aloud.",
                    ]},
                ],
            },
            {
                "key": "after_game",
                "heading": "Before You End The Meeting",
                "blocks": [
                    {"kind": "list", "items": [
                        "Read back the major fundraising decisions the Board has just adopted.",
                        "Read back each person's agreed execution responsibility so the transcript contains an unambiguous delegation record.",
                        "Confirm any roles or capacity the organization still needs to recruit.",
                        "Finish the meeting transcription only after the final delegation and accountability discussion is complete.",
                    ]},
                ],
            },
            {
                "key": "after_meeting",
                "heading": "After The Meeting",
                "blocks": [
                    {"kind": "list", "items": [
                        "If live transcription was used, confirm it saved successfully. If necessary, paste or upload the meeting transcript.",
                        "Allow the platform to compile the Final Board Fundraising Strategy from the Board's checked decisions, agreed discussion additions and transcript.",
                        "Review and adopt the final strategy.",
                        "Use the existing delivery flow to send the final strategy to every participant.",
                        "Create the existing Board Portfolios from each person's own participation choices plus the responsibilities they accepted during the meeting.",
                        "Board members continue through the existing Strategy → Portfolio → Execution Materials / Relationship Mapping → Executive Assistant journey.",
                    ]},
                ],
            },
        ],
    },
    "checklist": {
        "page_title": "Board Fundraising Day/Night Checklist",
        "intro": "Use this checklist to make sure your board, game and meeting are ready.",
        "groups": [
            {
                "key": "before",
                "heading": "Before The Meeting",
                "items": [
                    "Meeting details saved",
                    "Board members invited",
                    "Board members reminded to play the game",
                    "Board completion status reviewed",
                    "Group Game ready",
                    "Laptop ready",
                    "Internet connection ready",
                    "Screen-sharing or presentation setup ready",
                ],
            },
            {
                "key": "during",
                "heading": "During The Meeting",
                "items": [
                    "Explain the purpose of the session and get consent for transcription",
                    "Adopt funding audiences",
                    "Adopt where to find them",
                    "Adopt how to attract their attention",
                    "Adopt the fundraising process",
                    "Confirm team, individual roles and missing capacity",
                    "Approve the technology required",
                    "Approve the materials and content required",
                    "Approve the lean execution budget",
                    "Approve the 90–120 day execution and accountability sequence",
                    "Read back final delegation and missing roles",
                    "Finish and save the complete meeting transcript",
                ],
            },
            {
                "key": "after",
                "heading": "After The Meeting",
                "items": [
                    "Paste or upload meeting transcript",
                    "Generate Final Board Fundraising Strategy",
                    "Review final strategy",
                    "Review Board Portfolios",
                    "Review Execution Materials",
                    "Send final strategy to the board",
                    "Ask board members to complete Relationship Mapping",
                ],
            },
        ],
    },
}
