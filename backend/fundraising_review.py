"""Audience review actions on the existing Group Game session and strategy records."""
import copy
import os
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from member_auth import authenticate_member, require_entitlement, new_uuid
import fundraising_audiences as audience
from workflow_delivery import deliver_once


def now(): return datetime.now(timezone.utc).isoformat()


class AudienceReview:
    def __init__(self, db): self.db = db

    async def current(self, user_id):
        doc = await self.db.group_game_sessions.find_one({"user_id": user_id, "game_version": "audience-complete-v6", "status": {"$ne": "archived"}}, {"_id": 0})
        if not doc: raise HTTPException(409, "Prepare your audience review first")
        return doc

    async def prepare(self, user_id):
        existing = await self.db.group_game_sessions.find_one({"user_id": user_id, "status": {"$ne": "archived"}}, {"_id": 0}, sort=[("created_at", -1)])
        # Never replace an existing meeting, regardless of its workflow version.
        if existing: return existing
        members = await self.db.game_board_members.find({"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        responses = await self.db.game_audience_responses.find({"user_id": user_id, "completed": True}, {"_id": 0}).to_list(1000)
        proposals, statements = audience.proposed_audiences(responses, members)
        sid = "audience-review-" + user_id
        value = {"session_id": sid, "user_id": user_id, "token": secrets.token_urlsafe(24), "status": "waiting", "current_round": 0,
                 "game_version": "audience-complete-v6", "created_at": now(), "updated_at": now(),
                 "audience_review": {"revision": 0, "phase": "audiences", "index": 0, "proposals": proposals,
                                     "statements": statements, "decisions": {}, "commitments": [], "acknowledgements": {}}}
        await self.db.group_game_sessions.update_one({"_id": sid}, {"$setOnInsert": value}, upsert=True)
        return await self.current(user_id)

    async def state(self, session):
        result = copy.deepcopy(session)
        result.pop("_id", None)
        review = result["audience_review"]
        review["summary"] = audience.summary(review)
        people = await self.db.game_board_members.find({"user_id": session["user_id"], "removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
        review["people"] = [{"member_id": p["member_id"], "name": p["full_name"],
            "acknowledged": (review.get("acknowledgements", {}).get(p["member_id"], {}).get("revision") == review["summary"]["revision"])} for p in people]
        strategy = await self.db.game_strategies.find_one({"strategy_id": session.get("strategy_id", "")}, {"_id": 0})
        review["strategy"] = strategy
        return result

    async def save(self, session, review, **fields):
        revision = session["audience_review"]["revision"]
        review["revision"] = revision + 1
        result = await self.db.group_game_sessions.update_one({"session_id": session["session_id"], "audience_review.revision": revision},
                    {"$set": {"audience_review": review, "updated_at": now(), **fields}})
        if not result.modified_count: raise HTTPException(409, "The meeting changed. Refresh before saving again.")

    async def strategy(self, session):
        review = session["audience_review"]
        if review["phase"] not in {"adopted", "document", "approved"}: raise HTTPException(409, "Adopt the group's summary first")
        existing = await self.db.game_strategies.find_one({"strategy_id": "audience-" + session["session_id"]}, {"_id": 0})
        if existing: return existing
        agreed = audience.summary(review)
        profile = await self.db.game_profiles.find_one({"user_id": session["user_id"]}, {"_id": 0}) or {}
        sections = audience.document_sections(agreed, profile)
        body = "\n\n".join(s["title"] + "\n" + s["text"] for s in sections)
        roles = [{"name": c["name"], "board_member_id": c["member_id"], "role": c["contribution"], "contribution": c["contribution"], "confirmed": True} for c in agreed["commitments"]]
        record = {"strategy_id": "audience-" + session["session_id"], "user_id": session["user_id"], "mode": "final", "status": "final_draft", "version": 1,
            "schema_version": audience.VERSION, "share_token": secrets.token_urlsafe(24), "prepared_by": "The Board of " + (profile.get("organization") or {}).get("name", "your organization"),
            "data": {**{s["key"]: s["text"] for s in sections}, "board_roles": roles}, "section_edits": {s["key"]: s["text"] for s in sections},
            "document_sections": sections, "document_text": body, "source": "explicitly-adopted-audiences", "source_revision": agreed["revision"],
            "agreed_audiences": agreed["audiences"], "confirmed_commitments": agreed["commitments"], "generated_at": now(), "created_at": now()}
        await self.db.game_strategies.update_one({"strategy_id": record["strategy_id"]}, {"$setOnInsert": record}, upsert=True)
        await self.db.group_game_sessions.update_one({"session_id": session["session_id"]}, {"$set": {"strategy_id": record["strategy_id"]}})
        return await self.db.game_strategies.find_one({"strategy_id": record["strategy_id"]}, {"_id": 0})

    async def delivery(self, session):
        strategy = await self.strategy(session)
        if strategy["status"] != "adopted": raise HTTPException(409, "Approve the exact strategy before delivery")
        owner = await self.db.members.find_one({"user_id": session["user_id"]}, {"_id": 0}) or {}
        members = await self.db.game_board_members.find({"user_id": session["user_id"], "removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
        origin = (os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com").rstrip("/")
        recipients = {owner.get("email", ""): origin + "/game/group-game"}
        # Use each person's own existing secure final-strategy link.
        for person in members:
            if person.get("email") and person.get("token"):
                recipients.setdefault(person["email"], origin + "/game/final/" + person["token"])
        delivered = []
        for email, link in recipients.items():
            if email: delivered.append(await deliver_once(self.db, session["user_id"], "approved-strategy:" + strategy["strategy_id"], email,
                "Your Approved Board Fundraising Strategy", "Your board's approved fundraising strategy is saved. Use this secure link to read and download the exact version approved at your meeting, and begin the activities you agreed to undertake.", link))
        return delivered

    def router(self):
        router = APIRouter()
        async def host(request):
            member = await authenticate_member(request, self.db); require_entitlement(member, {"board_fundraising_game"})
            return await self.current(member["user_id"])

        @router.post("/game/group/audience/action")
        async def action(payload: dict, request: Request):
            session = await host(request); review = copy.deepcopy(session["audience_review"])
            if payload.get("revision") != review["revision"]: raise HTTPException(409, "Refresh to use the latest meeting decisions")
            operation = payload.get("action")
            if review["phase"] in {"document", "approved"}: raise HTTPException(409, "The agreed direction is already saved")
            if session["status"] not in {"in_progress", "completed"}: raise HTTPException(409, "Start the group review first")
            if operation in {"decision", "add", "progress", "commitment"} and review["phase"] not in {"audiences", "participation"}:
                raise HTTPException(409, "Return to discussion before changing decisions")
            if operation == "decision":
                proposal = next((p for p in review["proposals"] if p["id"] == payload.get("proposal_id")), None)
                if not proposal or payload.get("status") not in {"adopted", "rejected", "pending"}: raise HTTPException(422, "Choose a valid audience and decision")
                strategy = payload.get("strategy") or proposal["strategy"]
                value = {k: str(strategy.get(k) or "").strip()[:12000] for k in audience.FIELDS}
                if payload["status"] == "adopted" and not all(value.values()): raise HTTPException(422, "Complete the six agreed audience fields, or indicate uncertainty")
                review["decisions"][proposal["id"]] = {"status": payload["status"], "strategy": value}
            elif operation == "add":
                category = payload.get("category"); raw = payload.get("strategy") or {}
                if category not in audience.CATEGORIES or not all(str(raw.get(k) or "").strip() for k in audience.FIELDS): raise HTTPException(422, "Supply the complete audience agreed during discussion")
                sources = payload.get("source_ids") or []
                if not isinstance(sources, list) or any(i not in {p["id"] for p in review["proposals"]} for i in sources): raise HTTPException(422, "Choose valid source proposals")
                proposal = {"id": "discussion:" + new_uuid(), "category": category, "member_id": "", "contributor": "Board discussion", "source_ids": sources,
                            "strategy": {k: str(raw[k]).strip()[:12000] for k in audience.FIELDS}}
                review["proposals"].append(proposal)  # Explicit adoption is still required.
            elif operation == "progress":
                index = payload.get("index")
                if not isinstance(index, int) or index < 0 or index > len(review["proposals"]): raise HTTPException(422, "Choose a valid discussion step")
                review["index"] = index; review["phase"] = "participation" if index == len(review["proposals"]) else "audiences"
            elif operation == "commitment":
                person = await self.db.game_board_members.find_one({"user_id": session["user_id"], "member_id": payload.get("member_id"), "removed": {"$ne": True}}, {"_id": 0})
                contribution = str(payload.get("contribution") or "").strip()[:12000]
                if not person or not contribution or payload.get("confirmed") is not True: raise HTTPException(422, "Record a named person's explicitly agreed contribution")
                ids = payload.get("audience_ids") or []
                allowed = {p["id"] for p in audience.summary(review)["audiences"]}
                if not isinstance(ids, list) or any(i not in allowed for i in ids): raise HTTPException(422, "Connect commitments only to approved audiences")
                review["commitments"] = [c for c in review["commitments"] if c["member_id"] != person["member_id"]]
                review["commitments"].append({"member_id": person["member_id"], "name": person["full_name"], "contribution": contribution, "audience_ids": ids,
                    "next_action": str(payload.get("next_action") or "").strip()[:2000], "confirmed": True, "confirmed_at": now()})
            elif operation == "summary":
                approved = {p["id"] for p in audience.summary(review)["audiences"]}
                if any(i not in approved for c in review["commitments"] for i in c.get("audience_ids", [])):
                    raise HTTPException(422, "Update participation linked to an audience that is no longer adopted")
                if any(review["decisions"].get(p["id"], {}).get("status") not in {"adopted", "rejected"} for p in review["proposals"]): raise HTTPException(422, "Adopt or reject each audience before reviewing the complete strategy")
                review["phase"] = "summary"
            elif operation == "reopen": review["phase"] = "audiences"
            elif operation == "adopt":
                if review["phase"] != "summary" or payload.get("confirmed") is not True or payload.get("summary_revision") != audience.summary(review)["revision"]: raise HTTPException(409, "Review and confirm the current agreed strategy")
                if not audience.summary(review)["audiences"]: raise HTTPException(422, "Adopt at least one audience before generating a strategy")
                review["phase"] = "adopted"; review["facilitator_adopted_at"] = now()
            elif operation == "document":
                await self.strategy(session); review["phase"] = "document"
            else: raise HTTPException(422, "Unknown meeting action")
            await self.save(session, review)
            return {"saved": True}

        @router.post("/game/group/audience/document")
        async def approve_document(payload: dict, request: Request):
            session = await host(request); strategy = await self.strategy(session)
            if strategy["status"] == "adopted":
                await self.db.group_game_sessions.update_one({"session_id":session["session_id"]},{"$set":{"status":"completed","audience_review.phase":"approved"}})
                return {"status": "adopted", "delivery": await self.delivery(session)}
            if payload.get("source_revision") != strategy["source_revision"]: raise HTTPException(409, "Review the current strategy")
            sections = payload.get("sections")
            if not isinstance(sections, list) or [x.get("key") for x in sections] != [x["key"] for x in strategy["document_sections"]]: raise HTTPException(422, "Preserve the approved strategy's section structure")
            clean = [{"key": original["key"], "title": original["title"], "text": str(value.get("text") or "").strip()[:30000]} for original, value in zip(strategy["document_sections"], sections)]
            if any(not s["text"] for s in clean): raise HTTPException(422, "Keep the agreed content in each section")
            if payload.get("confirmed") is not True: raise HTTPException(422, "Confirm the exact wording before approval and email delivery")
            await self.db.game_strategies.update_one({"strategy_id": strategy["strategy_id"], "status": "final_draft"}, {"$set": {"status": "adopted", "adopted_at": now(),
                "document_sections": clean, "section_edits": {s["key"]: s["text"] for s in clean}, "document_text": "\n\n".join(s["title"] + "\n" + s["text"] for s in clean)}})
            review = copy.deepcopy(session["audience_review"]); review["phase"] = "approved"
            await self.save(session, review, status="completed", completed_at=now())
            await self.db.game_strategy_jobs.update_one({"user_id": session["user_id"], "mode": "final"}, {"$set": {"status": "completed", "strategy_id": strategy["strategy_id"], "finished_at": now()}}, upsert=True)
            return {"status": "adopted", "delivery": await self.delivery(session)}

        @router.post("/game/group/audience/retry-delivery")
        async def retry(request: Request): return {"delivery": await self.delivery(await host(request))}

        @router.get("/game/group/audience/download")
        async def download(request: Request):
            session = await host(request); strategy = await self.strategy(session)
            from strategy_pdf import build_strategy_pdf
            profile = await self.db.game_profiles.find_one({"user_id": session["user_id"]}, {"_id": 0}) or {}
            return Response(build_strategy_pdf(strategy, (profile.get("organization") or {}).get("name", "")), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="fundraising-strategy.pdf"'})

        @router.post("/game/group/play/{token}/acknowledge")
        async def acknowledge(token: str, payload: dict):
            session = await self.db.group_game_sessions.find_one({"token": token, "game_version": "audience-complete-v6", "status": {"$ne": "archived"}}, {"_id": 0})
            if not session: raise HTTPException(404, "This meeting link is not valid")
            person = await self.db.group_game_participants.find_one({"session_id": session["session_id"], "slot_id": payload.get("slot_id"), "device_id": payload.get("device_id")}, {"_id": 0})
            if not person: raise HTTPException(403, "Join with your own participant link first")
            review = copy.deepcopy(session["audience_review"]); revision = audience.summary(review)["revision"]
            if review["phase"] not in {"adopted", "document", "approved"} or payload.get("revision") != revision or payload.get("confirmed") is not True: raise HTTPException(409, "Review and acknowledge the current agreed strategy")
            # Independent acknowledgements never imply that an absent person agreed.
            review["acknowledgements"][person["board_member_id"]] = {"revision": revision, "acknowledged_at": now()}
            await self.save(session, review)
            return {"acknowledged": True}
        return router
