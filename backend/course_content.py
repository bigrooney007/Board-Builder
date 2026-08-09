"""Static Phase 2 course structure for the Recruitment programs.
Video URLs are configurable in the database (course_videos collection) — no code change needed.
"""

LINKEDIN_LAUNCH_INSTRUCTIONS = [
    "Finalize the board opportunity.",
    "Finalize the application link.",
    "Prepare the LinkedIn recruitment post.",
    "Publish from the appropriate LinkedIn profile or organization page.",
    "Ask board members and supporters to share it.",
    "Share with appropriate professional networks and groups where permitted.",
    "Personally send the opportunity to relevant professional contacts.",
    "Respond to comments and questions.",
    "Follow up with qualified prospects.",
    "Continue the campaign until there are enough qualified applicants.",
]

BASIC_MODULES = [
    {
        "number": 1,
        "title": "Identify the Board Members Your Organization Needs",
        "resources": [
            {"title": "Board Needs Worksheet", "content": "Use this worksheet to list the most important results your organization must accomplish in the next 12 months, the skills and relationships your present board already provides, and the specific gaps your new board members must fill."},
            {"title": "Board Profile Template", "content": "For each seat you want to fill, define the professional background, skills, networks, fundraising capacity and lived experience the ideal board member should bring, along with the expectations they must accept."},
            {"title": "Organizational Priorities Worksheet", "content": "Document your mission, the three most important organizational priorities for the next 12 months, and how the board must contribute to each priority."},
        ],
    },
    {
        "number": 2,
        "title": "Build Your Recruitment Strategy",
        "resources": [
            {"title": "Recruitment Strategy Template", "content": "Define who you are recruiting, why they would serve, where you will find them, the message you will use, who executes each step and how you will measure progress."},
            {"title": "Recruitment Timeline Template", "content": "Plan your campaign week by week: preparation, launch, active recruitment, interviews, references, selection and onboarding — with owners and dates for each stage."},
            {"title": "Recruitment Channel Guide", "content": "A guide to the recruitment channels that work for nonprofit boards: LinkedIn, professional associations, corporate volunteer programs, community networks, existing supporters and personal introductions — and how to use each one."},
        ],
    },
    {
        "number": 3,
        "title": "Launch Your Recruitment Campaign",
        "resources": [
            {"title": "Board Opportunity Template", "content": "A one-page board opportunity describing your mission, the impact of the organization, the role, the expectations, the time commitment and how to apply."},
            {"title": "Board Application Form Template", "content": "The application questions to collect: contact details, professional background, relevant skills, board experience, motivation for serving, availability and references."},
            {"title": "LinkedIn Recruitment Post Template", "content": "A ready-to-adapt LinkedIn post announcing your board opportunity: the hook, the mission statement, who you are looking for, what they will contribute and the application link."},
            {"title": "Social Media Recruitment Templates", "content": "Short-form recruitment posts adapted for Facebook, Instagram and X, each pointing to your board application."},
            {"title": "Recruitment Email Templates", "content": "Emails for announcing the opportunity to your supporters, personally inviting specific professionals, and following up with people who expressed interest."},
            {"title": "How to Launch Your Board Recruitment Campaign on LinkedIn", "is_linkedin_instructions": True, "content": "Follow these steps to launch your board recruitment campaign on LinkedIn.", "steps": LINKEDIN_LAUNCH_INSTRUCTIONS},
        ],
    },
    {
        "number": 4,
        "title": "Interview Your Applicants",
        "resources": [
            {"title": "Interview Invitation Template", "content": "An email inviting qualified applicants to a board interview, including scheduling details and what to expect."},
            {"title": "General Board Interview Guide", "content": "Structured interview questions covering motivation, relevant experience, fundraising willingness, availability, governance understanding and alignment with your mission."},
            {"title": "Interview Scorecard", "content": "A consistent scoring framework to evaluate each applicant across mission alignment, skills, networks, fundraising capacity, availability and board readiness."},
            {"title": "After-Interview Email Templates", "content": "Emails for advancing an applicant to references, keeping an applicant warm while you finish interviews, and respectfully declining applicants who are not a fit."},
        ],
    },
    {
        "number": 5,
        "title": "Complete References and Background Checks",
        "resources": [
            {"title": "Reference Request Email", "content": "An email asking an applicant’s reference for a short call or written response about the applicant’s reliability, follow-through and professional strengths."},
            {"title": "Reference Call Script", "content": "A short structured script for reference calls: relationship to the applicant, reliability, strengths, how they contribute in team settings and any reservations."},
            {"title": "Reference Evaluation Form", "content": "A form to record each reference conversation and evaluate whether the reference supports moving the applicant forward."},
            {"title": "Background Check Provider Resource Page", "content": "Guidance on when a background check is appropriate for board service and a list of established third-party background check providers. Nonprofit Board Builder does not perform background checks."},
        ],
    },
    {
        "number": 6,
        "title": "Onboard Your New Board Members",
        "resources": [
            {"title": "Onboarding Agenda", "content": "A structured agenda for the first onboarding session: welcome, mission and history, programs, finances, board expectations, key documents and first responsibilities."},
            {"title": "Organization Overview Template", "content": "A concise overview document covering your mission, history, programs, impact, finances, team and strategic priorities for new board members."},
            {"title": "Board Manual Template", "content": "The structure of a complete board manual: governing documents, board roster, committee descriptions, meeting calendar, policies and financial reports."},
            {"title": "Board Member Agreement Template", "content": "A written agreement describing the responsibilities, expectations, participation, giving and fundraising commitments each new board member accepts."},
            {"title": "Confidentiality Agreement Template", "content": "An agreement protecting the confidentiality of board discussions, donor information and organizational records."},
            {"title": "Conflict of Interest Agreement Template", "content": "A policy and disclosure agreement requiring board members to disclose and manage conflicts of interest."},
            {"title": "New Board Member 90-Day Plan Template", "content": "A 90-day plan giving each new board member clear first responsibilities, learning milestones and early contributions."},
        ],
    },
]

SELF_GUIDED_MODULES = [
    {
        "number": 1,
        "title": "Identify the Board Members Your Organization Needs",
        "workspace": {
            "heading": "Your Board Recruitment Workspace",
            "text": "This is where you will complete the deeper organizational and board profile used throughout your recruitment process.",
            "note": "Phase 3 will activate the execution workspace.",
        },
        "disabled_tools": [],
    },
    {
        "number": 2,
        "title": "Build Your Recruitment Strategy",
        "disabled_tools": ["Generate My Board Recruitment Strategy"],
        "tools_helper": "This tool will become available when the Recruitment Execution Tools are activated.",
    },
    {
        "number": 3,
        "title": "Launch Your Recruitment Campaign",
        "disabled_tools": [
            "Generate My Board Opportunity",
            "Generate My Board Application Form",
            "Generate My LinkedIn Recruitment Post",
            "Generate My Social Media Recruitment Posts",
            "Generate My Recruitment Emails",
            "Generate My LinkedIn Launch Instructions",
        ],
        "tools_helper": "These tools will become available when the Recruitment Execution Tools are activated.",
        "linkedin_section": {
            "heading": "Launching Your Recruitment Campaign on LinkedIn",
            "paragraphs": [
                "When the Recruitment Execution Tools are activated, the LinkedIn Launch Instructions generator will provide practical instructions for taking your completed board opportunity and actually launching it through LinkedIn.",
                "The instructions will explain where to post, how to structure the post, how to use your application link, how to ask others to share the opportunity, how to contact potential prospects, how to follow up, and how to maintain campaign activity until you have enough qualified applicants.",
                "LinkedIn activity is always executed by you — nothing is automated on LinkedIn.",
            ],
        },
    },
    {
        "number": 4,
        "title": "Interview Your Applicants",
        "future_areas": [
            "Applicant List",
            "Application Answers",
            "CV",
            "AI Interview Guide",
            "Interview Invitation",
            "Interview Status",
            "After-Interview Email",
        ],
        "tools_helper": "Applicant management will become available when the Recruitment Execution Tools are activated.",
        "disabled_tools": [],
    },
    {
        "number": 5,
        "title": "Complete References and Background Checks",
        "disabled_tools": [
            "Generate Reference Request Email",
            "Generate Reference Call Script",
            "Generate Reference Evaluation Form",
        ],
        "tools_helper": "These tools will become available when the Recruitment Execution Tools are activated.",
        "background_note": "External background-check resources will be available here.",
    },
    {
        "number": 6,
        "title": "Onboard Your New Board Members",
        "disabled_tools": [
            "Generate My Onboarding Agenda",
            "Generate My Organization Overview",
            "Generate My Board Manual",
            "Generate My Board Member Agreement",
            "Generate My Confidentiality Agreement",
            "Generate My Conflict of Interest Agreement",
            "Generate My New Board Member 90-Day Plan",
        ],
        "tools_helper": "These generators will be implemented in Phase 3.",
    },
]

PRODUCT_KEYS = {"recruitment_basic", "recruitment_self_guided"}

SUPPORT_TYPES = [
    "I have a question about this module",
    "I need help using the platform",
    "I need help executing this step",
    "I would like someone to help me complete this step",
]
