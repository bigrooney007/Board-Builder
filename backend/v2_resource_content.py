"""V2 resource inventory and adaptations of existing, reusable working templates.

Candidate-dependent resources are blank reusable templates. They do not assert an
interview, appointment, reference or consent has occurred.
"""
import re


# (key, title, group, existing generation type). No original registry is modified.
RECRUITMENT_INVENTORY = (
    ("recruitment_assessment_profiles", "Board Member Recruitment Profiles", "Organization and governance", "recruitment_assessment_profiles"),
    ("organization_overview", "Organization Overview", "Organization and governance", "organization_overview"),
    ("board_manual", "Board Manual", "Organization and governance", "board_manual"),
    ("board_member_agreement", "Board Member Agreement", "Organization and governance", "board_member_agreement"),
    ("confidentiality_agreement", "Confidentiality Agreement", "Organization and governance", "confidentiality_agreement"),
    ("conflict_of_interest_agreement", "Conflict of Interest Agreement", "Organization and governance", "conflict_of_interest_agreement"),
    ("board_profile_form", "Board Member Profile Form", "Organization and governance", ""),
    ("board_expectations", "Board Responsibilities and Expectations", "Organization and governance", ""),
    ("board_opportunity", "Board Recruitment Announcement", "Recruitment campaign", "board_opportunity"),
    ("board_recruitment_job_post", "Board Recruitment Job Post", "Recruitment campaign", "board_recruitment_job_post"),
    ("linkedin_post", "LinkedIn Recruitment Post", "Recruitment campaign", "linkedin_post"),
    ("social_posts", "Social Media Recruitment Posts", "Recruitment campaign", "social_posts"),
    ("recruitment_emails", "Recruitment Outreach Email", "Recruitment campaign", "recruitment_emails"),
    ("direct_invitation", "Direct Invitation for Prospective Board Members", "Recruitment campaign", ""),
    ("referral_request_email", "Recruitment Referral Request", "Recruitment campaign", "referral_request_email"),
    ("application_questions", "Board Application Form", "Recruitment campaign", "application_questions"),
    ("application_link", "Your Public Application Link", "Recruitment campaign", ""),
    ("launch_instructions", "Recruitment Launch Instructions", "Recruitment campaign", ""),
    ("general_interview_invitation", "Interview Invitation Email", "Interviews and communication", "general_interview_invitation"),
    ("general_interview_invitation_message", "Interview Invitation Short Message", "Interviews and communication", "general_interview_invitation_message"),
    ("interview_guidance", "Screening and Interview Guidance", "Interviews and communication", ""),
    ("rejection_email", "Application Rejection Email", "Interviews and communication", ""),
    ("candidate_followup", "Candidate Follow-up Email", "Interviews and communication", ""),
    ("after_interview_thank_you", "After-interview Thank-you Template", "Interviews and communication", ""),
    ("after_interview_rejection", "After-interview Rejection Template", "Interviews and communication", ""),
    ("reference_evaluation_form", "Reference-check Form", "References and appointments", ""),
    ("candidate_referee_request", "Reference Request Email", "References and appointments", ""),
    ("reference_request_email", "Reference Confirmation Email", "References and appointments", ""),
    ("reference_followup_email", "Reference Follow-up Email", "References and appointments", ""),
    ("reference_call_script", "Reference Call Guide", "References and appointments", ""),
    ("conditional_offer", "Conditional Appointment Email", "References and appointments", ""),
    ("unconditional_offer", "Unconditional Appointment Email", "References and appointments", ""),
    ("formal_appointment_letter", "Appointment Letter", "References and appointments", ""),
    ("acceptance_email", "Board Acceptance Template", "References and appointments", ""),
    ("onboarding_email", "Board Onboarding Email", "References and appointments", ""),
    ("onboarding_agenda", "Board Onboarding Agenda", "References and appointments", "onboarding_agenda"),
    ("onboarding_script", "Board Onboarding Facilitation Guide", "References and appointments", "onboarding_script"),
    ("portfolio_email", "Onboarding Portfolio Email Template", "References and appointments", ""),
    ("first_board_meeting_invitation", "First Board Meeting Invitation Template", "References and appointments", ""),
)


def normalize_copy(value):
    if isinstance(value, str):
        return value.replace("\u2014", ". ").replace("\u2013", "-")
    if isinstance(value, list):
        return [normalize_copy(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_copy(item) for key, item in value.items()}
    return value


def assert_allowed_content(text):
    # A failing generator is shown as retriable. It cannot quietly add an excluded service.
    if re.search(r"background[\s-]*check", str(text), re.I):
        raise ValueError("The generated resource contains an excluded service. Please retry generation.")


def organization_name(journey):
    return (journey.get("branding") or {}).get("organization_name") or journey.get("organization") or "Your organization"


def answer_value(journey, *keys):
    answers = journey.get("answers") or {}
    for key in keys:
        value = answers.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def signature(journey):
    return "\n".join(filter(None, (journey.get("name", ""), answer_value(journey, "founder_title", "title"), organization_name(journey))))


REFERENCE_QUESTIONS = (
    "In what capacity have you known or worked with [CANDIDATE NAME], and approximately how long have you known them?",
    "Based on your experience working with [CANDIDATE NAME], how would you describe their professionalism, reliability and ability to follow through on responsibilities they accept?",
    "What strengths have you observed in [CANDIDATE NAME] when working with other people, providing leadership, solving problems or contributing to shared goals?",
    "Is there anything relevant to [CANDIDATE NAME]'s professional conduct, reliability or ability to carry a position of responsibility that you believe we should understand as we consider their Board application?",
    "Based on your direct experience with [CANDIDATE NAME], would you be comfortable recommending them for a position of responsibility such as nonprofit Board service? Please briefly explain your answer.",
)


def reference_questions_text(blanks=False):
    return "\n\n".join(f"{index}. {question}" + ("\nReferee response: ______________________________\nNotes or clarification: ______________________________" if blanks else "") for index, question in enumerate(REFERENCE_QUESTIONS, 1))


def recruitment_template(key, journey, application_link):
    org, sign = organization_name(journey), signature(journey)
    mission = answer_value(journey, "organization_mission", "mission", "mission_statement", "q1")
    purpose = f"\n\nOur mission is: {mission}" if mission else ""
    templates = {
        "board_profile_form": (
            f"BOARD MEMBER PROFILE FORM\n\n{org}\n\nPlease complete the information you are comfortable sharing with your organization. This is an editable and printable profile form.\n\n"
            "PERSONAL AND CONTACT INFORMATION\nFull name: ____________________\nEmail: ____________________\nPhone: ____________________\nMailing address: ____________________\nLinkedIn profile: ____________________\n\n"
            "PROFESSIONAL BACKGROUND\nCurrent position: ____________________\nOrganization or employer: ____________________\nIndustry or professional field: ____________________\nProfessional expertise: ____________________\nProfessional certifications or licenses, if relevant: ____________________\nPrevious Board experience, if any: ____________________\n\n"
            "HOW YOU WOULD LIKE TO CONTRIBUTE\nWhich areas would you most like to contribute to as a member of the Board? ____________________\nOf the areas you selected, which would you be most interested in taking greater responsibility for helping the Board move forward, and what would you hope to help accomplish? ____________________\n\n"
            "LEADERSHIP INTEREST AND NETWORKS\nWould you be interested in a Board leadership or committee responsibility that aligns with your interests and experience? ____________________\nWhat type, if any? ____________________\nWhich professional or community relationships might you be comfortable helping the organization connect with? ____________________\nSelecting an area does not commit you to making introductions.\n\n"
            "STRENGTHS AND CAPACITY\nOther skills, resources, languages or experience: ____________________\nRealistic monthly hours for Board service: ____________________\nWhat would help you contribute effectively? ____________________\nWhy did you choose to join the organization? ____________________\nProfessional biography: ____________________\nProfessional headshot, if supplied separately: ____________________"
        ),
        "board_expectations": f"BOARD RESPONSIBILITIES AND EXPECTATIONS\n\n{org}{purpose}\n\nYour organization has supplied these expectations:\n\n" + (answer_value(journey, "board_expectations", "expectations", "board_responsibilities", "responsibilities") or "No specific time, meeting, term or fundraising requirements have been supplied. Confirm your expectations before sharing this resource with candidates.") + "\n\nUse your approved Board Manual and agreements to explain shared expectations. Agree individual contributions with each person. Do not turn expressions of interest into assigned responsibilities.",
        "application_link": f"YOUR PUBLIC APPLICATION LINK\n\n{application_link}\n\nYour form becomes available to applicants after you approve the required recruitment materials and confirm campaign launch. You can pause or close the campaign from the campaign page.",
        "direct_invitation": f"Subject: Consider Board service with {org}\n\nDear [PROSPECTIVE BOARD MEMBER NAME],\n\nI am writing to invite you to consider the Board opportunity at {org}.{purpose}\n\nOur approved recruitment announcement explains the experience we are looking for and how our Board contributes. Please review it and consider whether the opportunity aligns with your interests and capacity. If you would like us to consider your application, you can use the link below.\n\n{application_link}\n\nYou are welcome to ask us questions before applying. Thank you for considering the opportunity.\n\n{sign}",
        "launch_instructions": f"LAUNCH YOUR RECRUITMENT CAMPAIGN\n\nReview the announcement, job post, LinkedIn post and application questions. Edit anything that needs correction and approve the versions you want to share. Open the campaign preview and confirm launch. The launch results tell you whether the application form, marketplace listing and permitted applicant-network announcements succeeded.\n\nPROMOTE THE OPPORTUNITY\n\nAfter launch, share your approved LinkedIn post with your professional network. Use your social posts on Facebook and appropriate community pages, following their posting rules. Add your recruitment announcement and application link to your organization's website. Send your outreach and referral messages to your personal and professional contacts. Invite suitable people directly without assuming they want to join.\n\nYour application link is:\n{application_link}\n\nRespond to applications as they arrive. Your notification email opens the application directly, where you can review the person's information, prepare an interview guide and choose an invitation or respectful rejection message. You make selection and appointment decisions independently. The optional instructional video demonstrates an approximately 30-minute launch process.",
        "interview_guidance": "SCREENING AND INTERVIEW GUIDANCE\n\nReview what each applicant actually provided and compare it with your approved recruitment profiles and Board expectations. Use the applicant response page to generate a personalized interview guide. A missing CV does not establish a lack of capability.\n\nDiscuss the person's connection to your mission, relevant experience, examples of collaboration and follow-through, realistic availability and the contribution they would like to make. Ask consistent questions relevant to Board service. Avoid questions about protected characteristics or unrelated private circumstances.\n\nAn interview invitation is a request for a conversation. It does not appoint someone to your Board. Record what you heard and decide the next step yourself. Follow your organization's governing process when making appointment decisions.",
        "rejection_email": f"Subject: Thank you for your Board application\n\nDear [APPLICANT NAME],\n\nThank you for applying to the Board of {org} and for considering how you might contribute to our mission. We will not be moving your application forward to an interview.\n\nWe appreciate the time you took to consider the opportunity and wish you well.\n\n{sign}",
        "candidate_followup": f"Subject: Your Board application to {org}\n\nDear [APPLICANT NAME],\n\nThank you for your interest in serving on our Board. We are following up on your application and would welcome a reply so we can discuss the next step with you. Please let us know if you would still like to continue the conversation.\n\n{sign}",
        "after_interview_thank_you": f"Subject: Thank you for meeting with us\n\nDear [CANDIDATE NAME],\n\nThank you for taking the time to discuss the Board opportunity at {org}. We appreciate the chance to learn more about your interests and experience, and to answer your questions. We will contact you when we have confirmed our next step.\n\n{sign}\n\nUse this template only after the interview has taken place.",
        "after_interview_rejection": f"Subject: Thank you for meeting with us\n\nDear [CANDIDATE NAME],\n\nThank you for your application and the time you spent discussing the Board opportunity at {org}. We will not be moving your candidacy forward. We appreciate your interest in the organization and the opportunity to speak with you.\n\n{sign}\n\nUse this template only after the interview and your organization's decision.",
        "reference_evaluation_form": "REFERENCE RECORD AND EVALUATION FORM\n\nCandidate name: ____________________\nReferee name: ____________________\nReferee role and organization: ____________________\nRelationship to candidate: ____________________\nReference method, Email / Phone / Video / Other: ____________________\nDate reference completed: ____________________\nReviewer: ____________________\n\n" + reference_questions_text(True) + "\n\nREVIEWER'S RECORD\nRelevant strengths confirmed: ____________________\nRelevant concerns raised: ____________________\nInformation needing clarification: ____________________\n[ ] Reference completed, no further clarification needed.\n[ ] Reference completed, further clarification needed.\n\nComplete this record only after receiving a reference. No result is recorded automatically.",
        "candidate_referee_request": f"Subject: Professional references for your Board application\n\nDear [CANDIDATE NAME],\n\nAs we consider your Board application to {org}, please send the names and contact details of professional referees who have agreed to be contacted. Please describe how each referee knows you. We will use their direct experience to inform our conversation and decision.\n\n{sign}",
        "reference_request_email": f"Subject: Reference request for [CANDIDATE NAME]\n\nDear [REFEREE NAME],\n\nWe are considering [CANDIDATE NAME] for Board service with {org}. They have supplied your details as a professional referee. Would you be willing to reply with your direct experience in relation to the following questions?\n\n{reference_questions_text()}\n\nThank you for your time.\n\n{sign}",
        "reference_followup_email": f"Subject: Following up on a reference request\n\nDear [REFEREE NAME],\n\nI am following up on our reference request concerning [CANDIDATE NAME], who is being considered for Board service with {org}. If you are able to provide a reference, please reply to the questions in our original message. If you cannot assist, please let us know.\n\nThank you for considering our request.\n\n{sign}",
        "reference_call_script": f"REFERENCE CALL GUIDE\n\nHello [REFEREE NAME], this is {journey.get('name') or 'the organization leader'} from {org}. We are considering [CANDIDATE NAME] for Board service. Thank you for agreeing to share your direct experience.\n\n{reference_questions_text(True)}\n\nThank you for your time. Is there anything else relevant to their professional reliability or ability to serve in a position of responsibility that we should clarify?\n\nRecord the answers in your reference form. Do not treat an unanswered request as a completed reference.",
        "conditional_offer": f"Subject: Conditional Board appointment with {org}\n\nDear [CANDIDATE NAME],\n\nWe would like to offer you a Board appointment with {org}, subject to the following outstanding reference requirement that our organization has confirmed:\n\n[CONFIRMED REFERENCE CONDITION]\n\nWe will confirm the next step once that condition has been addressed. Please review the Board Manual and agreements and let us know any questions about our shared expectations.\n\n{sign}\n\nUse this template only after your organization has chosen the candidate and confirmed the actual reference condition. Replace the condition before sending.",
        "unconditional_offer": f"Subject: Your Board appointment with {org}\n\nDear [CANDIDATE NAME],\n\nWe are pleased to offer you a Board appointment with {org}, following our organization's decision. Please review the Board Manual and shared agreements and let us know whether you accept the appointment. We will coordinate the appropriate introduction and orientation with you directly.\n\n{sign}\n\nUse this template only after your organization has authorized the appointment.",
        "formal_appointment_letter": f"BOARD APPOINTMENT LETTER\n\n{org}\nIssue date: [ACTUAL ISSUE DATE]\n\nDear [CANDIDATE NAME],\n\nWe confirm your appointment to the Board of {org}, as authorized through our organization's governing process.\n\n[ACTUAL AGREED APPOINTMENT DETAILS, IF ANY]\n\nPlease use the Board Manual and shared agreements as the basis for understanding our expectations. We will confirm your agreed contribution and next steps directly with you. Thank you for agreeing to serve our organization.\n\n{sign}\n\nBefore issuing this letter, replace the date and any agreed details, remove unused fields and confirm that appointment has actually been authorized.",
        "acceptance_email": f"Subject: Acceptance of Board appointment to {org}\n\nDear {journey.get('name') or 'Organization Leader'},\n\nI accept the Board appointment offered by {org}. I have reviewed the shared expectations and would welcome confirmation of our agreed next steps.\n\n[BOARD MEMBER NAME]\n\nThis is a reply template for a person who has decided to accept an actual appointment offer.",
        "onboarding_email": f"Subject: Preparing for Board service with {org}\n\nDear [BOARD MEMBER NAME],\n\nThank you for agreeing to serve on our Board. Please review the Organization Overview, Board Manual, Board Member Agreement, Confidentiality Agreement and Conflict of Interest Agreement. Please also complete the Board Member Profile Form so we can understand your interests, strengths and available time.\n\nWe will agree the orientation arrangements directly with you and answer any questions about our shared expectations.\n\n{sign}\n\nSend the approved documents and profile form with this message. Add only confirmed meeting details. Use it after the person's appointment and acceptance.",
        "portfolio_email": f"Subject: Your agreed Board contribution at {org}\n\nDear [BOARD MEMBER NAME],\n\nThank you for discussing how you would like to contribute to {org}. We have recorded the contribution and support that we actually agreed. Please review that record and let us know if anything needs correction.\n\nWe will use our agreed next steps to guide your participation. Thank you for your willingness to contribute.\n\n{sign}\n\nAttach your organization's actual approved record of the conversation. This template does not create a portfolio or assign responsibilities.",
        "first_board_meeting_invitation": f"Subject: Your next Board meeting with {org}\n\nDear [BOARD MEMBER NAME],\n\nWe would like to invite you to the next confirmed Board meeting. Please add the actual date, time, timezone and location or meeting link before sending this invitation. We will share the agenda and papers so you can prepare.\n\n{sign}",
    }
    return normalize_copy(templates.get(key, ""))


def facilitation_guide(journey):
    org = organization_name(journey)
    fundraising = journey["product"] == "board-fundraising-game"
    topic = "fundraising strategy" if fundraising else "strategic plan"
    process = (
        "Review Individuals, Businesses and Grantmakers in turn. For each audience, discuss why it may support your mission, where you can find it, how you will attract its interest, how you will build the relationship, what you will ask it to support and the amount where known. Compare overlapping suggestions and preserve meaningful differences. Edit or combine the proposals you agree on. Mark each selected strategy as adopted and reject proposals you do not want. You can add an idea agreed during the discussion."
        if fundraising else
        "Review the existing strategic planning topics in turn. Read the source submissions, discuss the proposals and identify what your organization actually agrees to pursue. Edit or combine ideas when necessary and explicitly adopt the decisions you want in your plan. You may retain the existing mission by recording that as an adopted decision. Include budget and fundraising decisions only when the figures and commitments have been supplied and agreed."
    )
    participation = (
        "\n\nAGREE PARTICIPATION\n\nRead each person's participation statement. Ask which activity they would willingly support, what is realistic and what help they need. Record a commitment only after the person agrees. Connect it to the relevant adopted audience or activity. Nobody is assigned a responsibility automatically."
        if fundraising else ""
    )
    return f"FACILITATION GUIDE\n\n{org}\n\nBEFORE YOUR MEETING\n\nInvite people using their participation links and review the ideas as they arrive. Set your meeting details to support preparation and reminders. Your group session is available at any time, including before the meeting. Share the purpose of the discussion and ask everyone to read the contributions.\n\nOPEN THE DISCUSSION\n\nThank your board for its contributions. Explain that your task is to agree the {topic} your organization wants to use. The submitted ideas are suggestions until the group has discussed them and you confirm adoption. Follow your organization's existing process for making decisions.\n\nREVIEW AND ADOPT IDEAS\n\n{process}{participation}\n\nAPPROVE YOUR FINAL DOCUMENT\n\nGenerate the preview from the decisions you adopted. Read it together, correct anything that does not reflect your agreement and approve the final version. Your approved document will be saved, emailed and available to download. The organization carries out the agreed work independently."


def recommitment_templates(journey, form_link):
    from content_templates import recommitment_outreach_email
    org, sign = organization_name(journey), signature(journey)
    mission = answer_value(journey, "organization_mission", "mission", "mission_statement", "q1")
    goals = answer_value(journey, "organization_goals", "goals", "recommitment_goals")
    result = []
    for key, kind, title in (("recommitment_invitation", "initial", "Recommitment Invitation Email"), ("recommitment_followup_1", "reminder", "First Recommitment Follow-up")):
        message = recommitment_outreach_email(kind, "Board Member", journey.get("name", ""), answer_value(journey, "founder_title"), org, mission, goals)
        body = re.sub(r"\[COMPLETE MY[^\]]*\]", form_link, message["body"])
        result.append((key, title, f"Subject: {message['subject']}\n\n{body}"))
    result.append(("recommitment_followup_2", "Second Recommitment Follow-up", f"Subject: Please share your Board recommitment response\n\nDear Board Member,\n\nI am sending a final reminder about the recommitment form for {org}. Your response will help us understand your capacity, any concerns and how you would like to contribute moving forward.\n\nPlease complete the form using this link when you can:\n\n{form_link}\n\nIf you need more information or would prefer to talk first, please let me know. We want to have a clear and respectful conversation about your continued involvement.\n\nThank you,\n{sign}"))
    result.append(("recommitment_guidance", "Recommitment Guidance", "USING YOUR RECOMMITMENT MATERIALS\n\nExplain why you are inviting the Board to reflect and what you expect active service to involve. You can send your invitation through the platform or copy the message and form link into your own email account. Use the two follow-up templates for people who have not replied. External email delivery or opens cannot be tracked by this platform.\n\nAs people respond, your notification opens their submission directly. Read what they said and generate a conversation guide. Edit it, approve it and use your emailed copy to prepare. A completed form does not confirm a person's final recommitment. Agree any future contribution with the person during your conversation."))
    return [(key, title, normalize_copy(body)) for key, title, body in result]
