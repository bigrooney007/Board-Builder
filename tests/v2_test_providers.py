"""Fail-closed external provider doubles used only by synthetic V2 tests."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import types


def external_import_guards():
    """Permit importing existing services; any unmocked provider call fails."""
    guards = {}
    if importlib.util.find_spec("emergentintegrations") is None:
        for name in ("emergentintegrations", "emergentintegrations.llm", "emergentintegrations.llm.chat"):
            guards[name] = types.ModuleType(name)

        class NoNetworkChat:
            def __init__(self, *args, **kwargs):
                raise AssertionError("A V2 test attempted an unmocked AI provider call")

        class Message:
            def __init__(self, text):
                self.text = text

        guards["emergentintegrations.llm.chat"].LlmChat = NoNetworkChat
        guards["emergentintegrations.llm.chat"].UserMessage = Message
    return guards


class FakeStripe:
    def __init__(self):
        self.sessions = {}
        self.calls = []
        self.idempotency = {}
        self.fail_creation = False
        self.fail_retrieval = False
        self.checkout = types.SimpleNamespace(Session=types.SimpleNamespace(create=self.create, retrieve=self.retrieve))

    def create(self, **params):
        if self.fail_creation:
            raise RuntimeError("Synthetic Stripe outage")
        key = params.get("idempotency_key")
        if key in self.idempotency:
            return deepcopy(self.sessions[self.idempotency[key]])
        ident = f"cs_test_synthetic_{len(self.sessions) + 1}"
        unit_amount = params["line_items"][0]["price_data"]["unit_amount"]
        self.calls.append(deepcopy(params))
        self.sessions[ident] = {
            "id": ident, "url": f"http://testserver/test/checkout/{ident}",
            "expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600,
            "metadata": deepcopy(params["metadata"]), "mode": params["mode"], "currency": "usd",
            "amount_total": unit_amount, "amount_subtotal": unit_amount, "payment_status": "unpaid", "livemode": False,
            "client_reference_id": params["client_reference_id"], "customer_details": {"email": params["customer_email"]},
            "payment_intent": f"pi_test_synthetic_{len(self.sessions) + 1}",
        }
        self.idempotency[key] = ident
        return deepcopy(self.sessions[ident])

    def retrieve(self, ident, **options):
        if self.fail_retrieval:
            raise RuntimeError("Synthetic Stripe verification outage")
        return deepcopy(self.sessions[ident])

    def pay(self, ident):
        self.sessions[ident]["payment_status"] = "paid"


class FakeEmailTransport:
    def __init__(self):
        self.calls = []
        self.deliveries = {}
        self.fail_next = 0

    async def __call__(self, payload, idempotency_key):
        if any(not email.endswith("@example.test") for email in payload["to"]):
            raise AssertionError("Tests must never send to a real contact")
        self.calls.append((deepcopy(payload), idempotency_key))
        if self.fail_next:
            self.fail_next -= 1
            raise RuntimeError("Synthetic transient email failure")
        if idempotency_key not in self.deliveries:
            self.deliveries[idempotency_key] = f"email_test_{len(self.deliveries) + 1}"
        return self.deliveries[idempotency_key]


class FakeStructuredAI:
    """Schema-shaped provider output, retaining the real existing renderer.

    This does not certify real model writing quality. It exercises generation
    routing, source context, validation and branded artifact production offline.
    """
    def __init__(self):
        self.calls = []
        self.fail_types = set()
        self.excluded_types = set()

    async def __call__(self, generation_type, context, instructions=""):
        self.calls.append((generation_type, context, instructions))
        if generation_type in self.fail_types:
            raise RuntimeError("Synthetic AI provider failure")
        import ai_service
        source, _ = json.JSONDecoder().raw_decode(context.split("VERIFIED V2 CONTEXT:\n", 1)[1])
        organization = source["organization_name"]
        applicant = source.get("submission") or {}
        actual_answers = applicant.get("answers") or {}
        actual_concern = actual_answers.get("decision_reason") or actual_answers.get("participation_barriers") or actual_answers.get("why_interested") or ""
        sentence = f"{organization} serves its stated mission."
        if applicant:
            sentence = f"{applicant['name']} told {organization}: {actual_concern or 'I would like to discuss my contribution.'}"

        def fill(schema):
            if isinstance(schema, dict):
                return {key: fill(value) for key, value in schema.items()}
            if isinstance(schema, list):
                return [fill(schema[0])] if schema else []
            return sentence

        result = fill(ai_service.GENERATION_TYPES[generation_type]["schema"])
        if generation_type == "social_posts":
            result["posts"] = [{"platform": platform, "post_text": sentence + " Apply here: [APPLICATION LINK]"} for platform in ("LinkedIn", "Facebook", "Instagram")]
        if generation_type == "application_questions":
            result["custom_questions"] = [{"id": f"custom_{i}", "label": f"How would you help {organization}'s literacy work? Question {i}.", "type": "textarea", "why": "To understand the contribution you would like to make."} for i in range(1, 6)]
        if generation_type == "recruitment_assessment_profiles":
            result["priority_roles"] = [{"role_name": "Education governance", "why_this_person_is_important": sentence, "how_this_person_can_support": "Advise the board on the supplied education priorities."}]
        if generation_type == "interview_guide":
            result["candidate_name"] = applicant["name"]
            result["questions"] = [{"question": f"You mentioned {actual_concern}. Could you tell us more about your experience and available time?", "why_ask": "To understand what the applicant actually described.", "listen_for": "The applicant's examples and stated availability."} for _ in range(5)]
        if generation_type == "reactivation_conversation_script":
            result["member"] = applicant["name"]
            result["recommitment_response"] = actual_answers["recommitment"]
            result["what_they_told_you"] = actual_concern
            result["close_with_clear_next_steps"] = "Confirm what was actually agreed and what remains undecided."
        if generation_type in {"interview_invitation", "before_interview_rejection"}:
            result["subject"] = "Interview invitation" if generation_type == "interview_invitation" else "Thank you for your board application"
            result["body"] = f"Dear {applicant['name']},\n\n" + (f"Thank you for applying to {organization}. Please reply so we can agree a suitable interview time." if generation_type == "interview_invitation" else f"Thank you for your interest in {organization}. We have decided not to move your application to an interview.")
        if generation_type in self.excluded_types:
            result["excluded"] = "We completed a background check."
        return result
