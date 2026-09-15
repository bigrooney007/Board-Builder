"""Board Fundraising Game Phase 8: default host tools content (call script, facilitation guide, checklist)."""

DEFAULT_HOST_TOOLS = {
    "call_script": {
        "page_title": "Board Member Invitation Call Script",
        "intro": "Use this script when personally calling a board member before sending their invitation. You do not need to read it word for word. Use it to make sure you explain the purpose of the game clearly.",
        "sections": [
            {
                "key": "opening",
                "heading": "Opening",
                "body": "Hi [Board Member First Name], I wanted to speak with you briefly about something we are doing at our next board meeting.\n\n[Organization Name] is working toward a fundraising goal of [Fundraising Goal] by [Fundraising Deadline], and instead of bringing in one person to create the fundraising strategy for us, we are going to build it together as a board.",
            },
            {
                "key": "explain_game",
                "heading": "Explain The Game",
                "body": "We are going to play something called the Board Fundraising Game.\n\nBefore the meeting, every board member will receive a personal link. You will go through a guided fundraising game that helps you think through how you believe we can raise the money.\n\nYou do not need fundraising experience. The game actually teaches you how a fundraising strategy is built while helping you contribute your own ideas.",
            },
            {
                "key": "think_about",
                "heading": "What They Will Think About",
                "body": "You will think about who could fund our mission, where we can find them, how we can attract them, the process we should use to raise money, the technology we need, who should be involved in fundraising, the materials we need and what our execution timeline should look like.\n\nYou will also tell us how you personally want to help build our fundraising system and how you want to participate in raising money.",
            },
            {
                "key": "game_night",
                "heading": "Explain Game Night",
                "body": "Then during our board meeting, we will bring everybody's ideas together.\n\nYou will see the ideas contributed by the board and help rank the strongest ones.\n\nThose collective decisions will become the foundation of our fundraising strategy.\n\nWe will review the strategy together, make any final changes and adopt the plan we want the organization to execute.",
            },
            {
                "key": "expectation",
                "heading": "Set The Expectation",
                "body": "The most important thing I need from you before the meeting is to complete your individual game.\n\nYou can complete one section at a time and return later if you need to, but please complete it before Game Night so your ideas are included when we play together.",
            },
            {
                "key": "close",
                "heading": "Close",
                "body": "I will send your invitation shortly. It will contain your personal game link and the details for Game Night.\n\nI am looking forward to seeing what everyone brings to the table because this strategy is going to be built by us as a board.",
            },
        ],
    },
    "facilitation": {
        "page_title": "Board Fundraising Game Facilitation Guide",
        "sections": [
            {
                "key": "before_meeting",
                "heading": "1. Before The Meeting Starts",
                "blocks": [
                    {"kind": "list", "items": [
                        "Make sure the Board Fundraising Game dashboard is open",
                        "Make sure the Group Review Game has been prepared",
                        "Copy the shared Group Game link",
                        "Confirm how many board members completed their Individual Game",
                        "Make sure the Board-Prioritized Strategy can be generated after the Review Game",
                        "Open your video meeting separately if meeting online",
                        "Have the fundraising goal visible",
                        "Make sure everyone has access to their phone, tablet or computer",
                    ]},
                    {"kind": "note", "label": "Host Reminder", "text": "Do not begin by teaching the entire fundraising strategy again. Your board has already learned through the Individual Game. Your job during Game Night is to help them make decisions together."},
                ],
            },
            {
                "key": "open_game_night",
                "heading": "2. Open Game Night",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "Thank you everyone for being here.\n\nOur goal tonight is very specific. [Organization Name] wants to raise [Fundraising Goal] by [Fundraising Deadline].\n\nBefore tonight, each of you had the opportunity to think individually about how we can raise that money.\n\nTonight we are bringing those ideas together.\n\nWe are going to review what the board contributed, identify our strongest priorities and use those decisions to build the fundraising strategy we will execute together."},
                    {"kind": "script", "text": "This is not about one person's idea winning. We are trying to identify the strongest combination of ideas for the organization."},
                    {"kind": "script", "text": "Please open the link I am sharing now and select your name."},
                    {"kind": "group_link"},
                ],
            },
            {
                "key": "play_review_game",
                "heading": "3. Play The Review Game",
                "blocks": [
                    {"kind": "text", "text": "The Review Game contains eight rounds. Everyone ranks ideas independently before the group sees the result."},
                    {"kind": "numbered", "label": "The Rounds", "items": [
                        "Who Should Fund Us?",
                        "Where Can We Find Them?",
                        "How Will We Attract Them?",
                        "What Fundraising Process Should We Use?",
                        "What Technology Do We Need?",
                        "Who Do We Need On The Fundraising Team?",
                        "What Materials And Tools Do We Need?",
                        "What Should Our Execution Timeline Prioritize?",
                    ]},
                    {"kind": "script", "label": "Host Script", "text": "For each round, take a moment to read every idea before ranking.\n\nChoose the ideas you genuinely believe should receive the greatest attention.\n\nYour individual ranking will remain hidden until voting closes."},
                    {"kind": "numbered", "label": "Host Process For Every Round", "items": [
                        "Open the round.",
                        "Ask everyone to read all the ideas.",
                        "Give everyone time to submit.",
                        "Watch the submitted count.",
                        "Close voting when the group is ready.",
                        "Show the Board Priorities.",
                        "Briefly acknowledge the result.",
                        "Continue to the next round.",
                    ]},
                    {"kind": "script", "label": "Host Language After Each Result", "text": "These are the ideas the board collectively prioritized. The other ideas are still being saved, so we are not losing anything."},
                    {"kind": "text", "text": "Do not encourage a long debate after every ranking round. The strategy review later is where deeper discussion happens."},
                ],
            },
            {
                "key": "decisions_to_strategy",
                "heading": "4. Turn The Board's Decisions Into A Strategy",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "We have now identified our collective fundraising priorities.\n\nThe next step is turning those decisions into an actual fundraising strategy."},
                    {"kind": "numbered", "label": "Host Steps", "items": [
                        "Open the Group Game Results.",
                        "Review Board Priorities and Additional Board Ideas.",
                        "Move or reorder anything only if the board agrees something needs adjustment.",
                        "Click: Generate Our Fundraising Strategy",
                        "Wait for the Board-Prioritized Draft to finish generating before continuing.",
                    ]},
                ],
            },
            {
                "key": "review_strategy",
                "heading": "5. Review The Fundraising Strategy Together",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "We now have a complete fundraising strategy built from the information about our organization and the priorities we selected together.\n\nWe are going to review it one section at a time.\n\nAs we review, I want everyone to think about whether the strategy accurately reflects what we believe the organization should do.\n\nYou will be able to approve each section, suggest a change or identify something we need to discuss further."},
                    {"kind": "script", "text": "Our goal is to leave this meeting with a strategy we understand, agree with and are prepared to execute."},
                ],
            },
            {
                "key": "capture_discussion",
                "heading": "6. Capture The Discussion",
                "blocks": [
                    {"kind": "text", "text": "If you want the platform to help capture decisions from the discussion, turn on Live Transcript before beginning the detailed strategy review."},
                    {"kind": "text", "text": "Make sure everyone knows that live transcription is being used before turning it on."},
                    {"kind": "button_label", "text": "Start Live Transcript"},
                    {"kind": "text", "label": "Host Guidance", "text": "You do not need to narrate for the transcript. Facilitate the meeting normally. The transcript is there to help capture agreements, suggested changes, commitments and unresolved issues."},
                ],
            },
            {
                "key": "review_sections",
                "heading": "7. Review Each Strategy Section",
                "blocks": [
                    {"kind": "text", "text": "For each strategy section the host should ask two questions."},
                    {"kind": "script", "label": "Question 1", "text": "Does this accurately reflect what we believe the organization should do?"},
                    {"kind": "script", "label": "Question 2", "text": "Is there anything we need to change, add, remove or clarify before this becomes part of our final strategy?"},
                    {"kind": "note", "label": "Facilitation Rule", "text": "Do not rewrite sections simply because one person prefers different wording. Focus discussion on strategic decisions that materially change what the organization will do."},
                    {"kind": "text", "text": "If the board agrees on a change, either edit the section directly or allow the meeting discussion to be captured for decision processing later."},
                ],
            },
            {
                "key": "execution_commitments",
                "heading": "8. Listen For Execution Commitments",
                "blocks": [
                    {"kind": "text", "text": "As the board discusses the strategy, listen for statements about how people want to participate."},
                    {"kind": "list", "label": "Examples", "items": [
                        "\"I can introduce us to some local businesses.\"",
                        "\"I can help oversee the CRM.\"",
                        "\"I would be willing to steward some of the corporate partners.\"",
                        "\"I can help recruit volunteers for the fundraising team.\"",
                    ]},
                    {"kind": "text", "text": "Do not stop the strategy review every time someone volunteers. The meeting transcript can capture these commitments and the platform will surface them later for review."},
                ],
            },
            {
                "key": "process_decisions",
                "heading": "9. Process Your Board's Decisions",
                "blocks": [
                    {"kind": "numbered", "label": "After Finishing The Strategy Review", "items": [
                        "Click: Review Meeting Decisions",
                        "Click: Analyse Meeting Discussion",
                        "Review each proposed decision.",
                        "Accept, reject or edit the suggested changes.",
                        "Resolve any items the board clearly decided.",
                        "Leave genuinely unresolved items unresolved.",
                        "Review any execution commitments identified during the meeting.",
                    ]},
                    {"kind": "note", "label": "Important", "text": "The AI analysis is proposing what it believes the board decided. You remain responsible for confirming which decisions should actually change the strategy."},
                ],
            },
            {
                "key": "final_strategy",
                "heading": "10. Create The Final Fundraising Strategy",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "We have reviewed the strategy and confirmed the decisions made during our discussion.\n\nI am now going to create the Final Fundraising Strategy using the changes we agreed together."},
                    {"kind": "numbered", "label": "Host Steps", "items": [
                        "Click: Generate Final Fundraising Strategy",
                        "Once ready, open the Final Draft.",
                    ]},
                ],
            },
            {
                "key": "final_review",
                "heading": "11. Review The Final Strategy",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "This is the final version reflecting the priorities we selected and the changes we agreed during our discussion.\n\nPlease review it carefully."},
                    {"kind": "text", "text": "At the end, you will be able to approve the Final Strategy or request another change."},
                    {"kind": "note", "label": "Host Guidance", "text": "If a change request is minor and the board agrees immediately, edit the Final Draft manually.\n\nGenerate another AI version only when the change requires the strategy to be regenerated.\n\nThis is important for cost control."},
                ],
            },
            {
                "key": "adopt_strategy",
                "heading": "12. Adopt The Fundraising Strategy",
                "blocks": [
                    {"kind": "script", "label": "Host Script", "text": "If there are no further changes that prevent us from moving forward, we now need to decide whether we are ready to adopt this as our organization's fundraising strategy."},
                    {"kind": "text", "text": "Once adopted, this becomes the working fundraising strategy we will execute toward our [Fundraising Goal] goal.\n\nThe organization should follow its normal board decision-making process."},
                    {"kind": "numbered", "label": "After That Process", "items": [
                        "Click: Adopt This Fundraising Strategy",
                        "Complete the adoption confirmation.",
                    ]},
                ],
            },
            {
                "key": "strategy_to_execution",
                "heading": "13. Move From Strategy To Execution",
                "blocks": [
                    {"kind": "script", "label": "Host Script (After Adoption)", "text": "We now have an adopted fundraising strategy.\n\nThe final part of our process is making sure everyone knows how they want to contribute to executing it.\n\nBefore Game Night, each of you told us how you would like to help build the fundraising system and how you would like to help raise money directly.\n\nThe platform will combine those choices with any commitments you made tonight and create your individual Board Fundraising Portfolio."},
                    {"kind": "script", "text": "You will receive your portfolio after the meeting. You will review it, request any changes if necessary and approve the role you are prepared to play."},
                ],
            },
            {
                "key": "close_game_night",
                "heading": "14. Close Game Night",
                "blocks": [
                    {"kind": "script", "label": "Closing Script", "text": "Thank you for the thinking and decisions you brought into this process.\n\nWe came into this meeting with a fundraising goal.\n\nWe are leaving with an adopted fundraising strategy built with the board.\n\nThe next step is execution.\n\nYou will receive your personal Board Fundraising Portfolio showing how you can help build the fundraising system and support fundraising directly. Once you approve it, you will also be able to generate the materials you need to execute your role.\n\nFrom this point forward, the strategy becomes something we work from, review and execute together."},
                ],
            },
        ],
    },
    "checklist": {
        "page_title": "Game Night Preparation Checklist",
        "intro": "Use this checklist before your board meeting so Game Night can focus on decisions instead of administration.",
        "groups": [
            {
                "key": "days7",
                "heading": "7+ Days Before Game Night",
                "items": [
                    "Game Night date and time are confirmed",
                    "All participating board members have been added",
                    "Invitations have been sent",
                    "Board members understand why they are playing the game",
                    "Individual Game links are working for the intended board members",
                    "Meeting location or external video meeting link is confirmed",
                    "Fundraising goal and deadline are correct",
                ],
            },
            {
                "key": "days2_3",
                "heading": "2-3 Days Before Game Night",
                "items": [
                    "Review Individual Game completion progress",
                    "Send reminders to eligible board members who have not finished",
                    "Check that enough board ideas have been submitted to play the Review Game",
                    "Confirm the meeting link/location with participants",
                    "Review the Facilitation Guide",
                    "Confirm that the organization's Fundraising Game Profile is accurate",
                ],
            },
            {
                "key": "before_meeting",
                "heading": "Before The Meeting Starts",
                "items": [
                    "Open the Board Fundraising Game dashboard",
                    "Prepare the Group Review Game",
                    "Copy the shared Group Game link",
                    "Open the video meeting platform if meeting online",
                    "Confirm the correct fundraising goal is visible",
                    "Make sure participants have a device they can use for ranking",
                    "Decide whether Live Transcript will be used",
                    "Inform participants if transcription will be used",
                    "Open the Facilitation Guide",
                ],
            },
            {
                "key": "during",
                "heading": "During Game Night",
                "items": [
                    "Explain the goal of Game Night",
                    "Share the Group Game link",
                    "Confirm participants have joined",
                    "Complete all eight Review Game rounds",
                    "Generate the Board-Prioritized Strategy",
                    "Review the strategy section by section",
                    "Capture agreed changes",
                    "Capture execution commitments",
                    "Process meeting decisions",
                    "Generate the Final Strategy",
                    "Complete the final strategy review",
                    "Complete the organization's normal adoption process",
                    "Adopt the strategy in the platform",
                ],
            },
            {
                "key": "after",
                "heading": "After Game Night",
                "items": [
                    "Confirm the adopted strategy is available",
                    "Create Board Fundraising Portfolios",
                    "Review each portfolio",
                    "Send portfolios to participating board members",
                    "Monitor portfolio approvals",
                    "Resolve requested changes",
                    "Confirm approved board members can access their Execution Toolkit",
                ],
            },
        ],
    },
}
