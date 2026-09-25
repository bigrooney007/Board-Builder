"""Default static content for the Board Fundraising Day/Night host tools (no AI)."""

DEFAULT_HOST_TOOLS = {
    "call_script": {
        "page_title": "Call Script",
        "intro": "Use this script to make sure every board member completes their Board Fundraising Game before your meeting. The invitation is already in their inbox.",
        "sections": [
            {
                "key": "script",
                "heading": "Call Script",
                "body": "Hi [Board Member First Name], I wanted to make sure you saw the Board Fundraising Game invitation we sent to your email.\n\nBefore our next board meeting on [Meeting Date], we need every board member to play the game.\n\nIt will help you identify the individuals, businesses and grantors with the strongest reason to support our goal, why they would give, where to find them, how to attract them, what to ask them to fund, the process for raising money from them and how you would feel comfortable helping.\n\nYour ideas will be brought into the Board Fundraising Day/Night so we can build the fundraising strategy together.\n\nThe game is already waiting for you in your inbox.\n\nPlease complete it before the meeting.\n\nIf you cannot find the email, let me know and I will resend it.",
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
                        "FUNDING AUDIENCES AND WHY — Review every proposed individual, business and grantor audience together with the reason each participant believes they will support the goal. Compare these ideas with the organization's present supporters. Check every audience and reason the Board agrees to pursue.",
                        "WHERE TO FIND THEM — Review the places, networks, relationships and search methods. Check the ones the Board believes it can execute consistently.",
                        "HOW TO ATTRACT THEM AND BUILD CREDIBILITY — Review the value, content, experiences, partnership benefits and credibility ideas. Check what fits each chosen audience and the organization's real capacity.",
                        "WHAT TO ASK FOR AND HOW MUCH — For individuals, businesses and grantors, agree what part of the goal they should fund and the amount or range the organization should ask from each suitable prospect.",
                        "FUNDRAISING PROCESS — Agree how each chosen audience moves from first contact through Know, Like, Trust, Ask, Follow Up and Stewardship. Preserve any present method the Board wants to continue and make the next action clear.",
                        "BOARD ROLES — Review how every participant said they would feel comfortable and useful helping. Ask each person to confirm, change or decline a specific responsibility. Say the final role, action and timing aloud so the transcript contains an unambiguous delegation record.",
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
                        "Review and confirm the proposed responsibility for every participant, then start delegation.",
                        "Send one email containing each participant's strategy, Board Fundraising Portfolio and personal fundraising assistant links.",
                        "About 24 hours later, send the separate Relationship Mapping email so Board Members can recommend suitable contacts from their networks.",
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
                    "Adopt funding audiences and why they will support the goal",
                    "Adopt where to find them",
                    "Adopt how to attract them and build credibility",
                    "Adopt what each audience should fund and how much to ask",
                    "Adopt the fundraising process",
                    "Confirm each participant's fundraising role and first action",
                    "Read back every final delegation",
                    "Finish and save the complete meeting transcript",
                ],
            },
            {
                "key": "after",
                "heading": "After The Meeting",
                "items": [
                    "Generate Final Board Fundraising Strategy",
                    "Review, edit and adopt the final strategy with every participant",
                    "Review and confirm Board Member delegation",
                    "Send the strategy, Portfolio and assistant email",
                    "Send the separate Relationship Mapping email about 24 hours later",
                ],
            },
        ],
    },
}
