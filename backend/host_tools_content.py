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
                    {"kind": "list", "items": [
                        "Move through all four strategic areas.",
                        "Allow board members to review and rank the ideas.",
                        "Close voting only when everyone participating has finished.",
                        "Show the results.",
                        "Discuss anything the board wants clarified, changed or added.",
                        "Continue until all four strategic areas are complete.",
                    ]},
                ],
            },
            {
                "key": "after_game",
                "heading": "After The Group Game",
                "blocks": [
                    {"kind": "list", "items": [
                        "Continue the board discussion.",
                        "Discuss implementation, responsibilities, additional ideas and any changes the board wants reflected in the final strategy.",
                        "Keep a transcript of the rest of the meeting.",
                    ]},
                ],
            },
            {
                "key": "after_meeting",
                "heading": "After The Meeting",
                "blocks": [
                    {"kind": "list", "items": [
                        "Paste or upload the meeting transcript into the dashboard.",
                        "Allow the platform to compile the Final Board Fundraising Strategy.",
                        "Review the final strategy.",
                        "Send the final strategy to board members.",
                        "Board members can then review their personal Board Portfolio, Execution Materials and Relationship Mapping Form.",
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
                    "Explain the purpose of the session",
                    "Complete Strategic Area 1",
                    "Complete Strategic Area 2",
                    "Complete Strategic Area 3",
                    "Complete Strategic Area 4",
                    "Review board priorities",
                    "Discuss additional ideas",
                    "Discuss responsibilities and execution",
                    "Capture meeting transcript",
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
