"""FINAL active narration library — exactly NINE static clips (owner's exact scripts, one continuous
passage each; sent to ElevenLabs as ONE TTS request per clip). All previous narration versions are
INACTIVE (stored audio remains in db.game_voice_audio, unreferenced). NO personalized narration."""

TEXTS = {
    "a1_intro": "Fundraising gets a lot easier when you know exactly who has the strongest reason to care about your mission. If you try to raise money from everybody, you end up asking randomly. A fundraising system starts by identifying the exact people, businesses and grantors most likely to want your mission to succeed. So let's start there. Who do you think are the exact types of people, businesses and grantors with the greatest reason to fund your mission?",
    "a1_deeper": "Now let's go deeper. Don't stop at broad answers like parents, businesses or foundations. Ask yourself who has experienced the problem you solve, who knows someone affected by it, who works around the issue, who serves the same people, who benefits when the problem is solved and who already supports work connected to your mission. For businesses, think about who employs, serves or sells to the people you help, or has a reason to invest in the community you serve. For grantors, think about who already funds your issue, your population, your location or your type of program. The goal is to get specific enough that you could actually go out and find them. Based on that, who specifically should your organization be looking for?",
    "a2_intro": "Knowing who should fund your mission is only useful if you know where to consistently find them. Fundraising becomes a system when you have repeatable places where the exact people, businesses and grantors you want already gather, work, network, learn or can be identified. So now let's find those places. Where do you think you can consistently find the people, businesses and grantors you identified?",
    "a2_deeper": "Think about where each audience already congregates. If you are looking for Christians, you go to the church. If you are looking for Muslims, you go to the mosque. The same principle applies here. People may gather in professional associations, community groups, churches, schools, events, Facebook groups, LinkedIn communities or local networks. Businesses may be found through chambers, trade groups, directories, industry events and LinkedIn. Grantors may be found through funding databases, community foundations, funder networks, existing grantee lists, information sessions and program officers. You do not need to search everywhere. You need to know where your exact funders already are. Based on that, where should your organization consistently go to find them?",
    "a3_intro": "Finding potential funders is not enough. If every interaction begins with asking people for money, you will spend your time chasing people. A fundraising system gives the right people a reason to notice your organization, connect with you and give you the opportunity to build a relationship before the ask. So what can your organization offer the people, businesses and grantors you identified that would make them want to stop, pay attention and connect with you?",
    "a3_deeper": "Now think about what would genuinely be useful, interesting or meaningful to the people you want to reach. It could be a guide, report, survey, checklist, assessment, educational session, event, community activity, campaign, useful resource, opportunity to share an opinion or an invitation to contribute to something meaningful. For businesses, it could simply be a reason to open a conversation around a shared community interest. For grantors, it may begin with understanding what they fund, attending their sessions, asking good questions and building familiarity with the people responsible for their priorities. The goal is simple. Give the right funders a reason to move toward your organization before you ask them for money. Based on that, what can you offer your potential funders?",
    "a4_intro": "Once potential funders connect with your organization, you need a clear process for moving that relationship toward financial support. You do not raise money consistently by meeting someone and immediately asking them for money. You need a process that builds familiarity, interest and trust before the ask, then keeps the relationship going afterward. Once potential funders connect with your organization, how do you think you should raise money from them?",
    "a4_deeper": "The process is know, like, trust, ask, follow up and steward. First, they need to know who you are and understand what you do. Then they need reasons to stay connected and become interested. Trust grows when they see your impact, leadership and ability to do what you say. Then you make a clear ask. If they are not ready, you follow up instead of disappearing. And when they give, you steward the relationship by thanking them, showing what their support made possible and continuing the connection. That is how fundraising becomes a repeatable system instead of constantly chasing strangers. Based on this process, how should your organization move potential funders from first connection to financial support and an ongoing relationship?",
    "approval_review": "I've cleaned up what you shared so it is clearer and easier to use. Take a look at both versions and choose the one you want to keep.",
}

LABELS = {
    "a1_intro": "Area 1 Introduction + First Question",
    "a1_deeper": "Area 1 Teaching + Stronger Question",
    "a2_intro": "Area 2 Introduction + First Question",
    "a2_deeper": "Area 2 Teaching + Stronger Question",
    "a3_intro": "Area 3 Introduction + First Question",
    "a3_deeper": "Area 3 Teaching + Stronger Question",
    "a4_intro": "Area 4 Introduction + First Question",
    "a4_deeper": "Area 4 Teaching + Stronger Question",
    "approval_review": "Generic Fine-Tuned Idea Review",
}

STATIC_NARRATIONS = [{"narration_id": nid, "game_step_id": nid, "label": LABELS[nid]} for nid in TEXTS]

PERSONALIZED_POINTS = []

DEFAULT_VOICE_SETTINGS = {
    "voice_enabled": True,
    "read_type_enabled": True,
    "default_mode": "voice",
    "narration_on": True,
    "personalization_on": False,
    "max_personal_clips": 0,
    "voice_provider": "elevenlabs",
    "voice_id": "",
    "browser_stt_on": False,
    "generic_fallback_on": True,
}
