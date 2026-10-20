"""Guided-service adapter for the existing Strategic Planning forms and meeting engine.

Uses sp_projects, sp_participants, sp_forms, sp_sessions and sp_plans. Existing
legacy projects never enter these branches. No fundraising-game handlers are used.
"""
import base64
import copy
import io
import json
import re
import secrets
from contextvars import ContextVar
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

import strategic_questionnaire as questionnaire
from auth_service import authenticate_admin

_request = ContextVar("guided_planning_request", default=None)
SECTIONS = ["vision", "goals", "programs", "beneficiaries", "present_reality", "people", "technology", "marketing", "partnerships", "fundraising", "budget", "risks", "action_planning", "measurement", "participation"]
TITLES = {"vision":"Vision", "goals":"Goals", "objectives":"Objectives", "programs":"Programs", "beneficiaries":"People We Serve", "present_reality":"Our Present Position", "people":"People and Teams", "technology":"Technology and Infrastructure", "marketing":"Marketing and Community Engagement", "partnerships":"Partnerships", "fundraising":"Fundraising", "budget":"Financial Capacity", "risks":"Risks", "action_planning":"Action Priorities", "measurement":"Progress and Review", "participation":"Personal Participation"}

def planning_questions(group, originals):
    rows=[]
    for q, section in zip(originals, SECTIONS):
        prompt=q["prompt"] if group=="leader" else "What would you recommend? " + q["prompt"]
        rows.append({"id":q["key"],"key":q["key"],"prompt":prompt,"help":q.get("help", ""),"required":True,"type":"textarea","options":[],"archived":False,"section_key":section,"section_title":TITLES[section],"per_program":section=="programs"})
        if section=="goals":
            rows.append({"id":"planning_objectives","key":"planning_objectives","prompt":"What specific objectives would help your organization achieve these goals?" if group=="leader" else "Which specific objectives would you recommend to help the organization achieve its goals?","help":"Explain the practical results you would like the organization to achieve.","required":True,"type":"textarea","options":[],"archived":False,"section_key":"objectives","section_title":"Objectives","per_program":False})
        if section=="programs":
            rows.append({"id":"program_proposals","key":"program_proposals","prompt":"Would you recommend a new program or a change to the programs we offer?","help":"Describe any proposed new program, or a program you believe should change or end. Explain why. If you have no additional suggestion, you can leave this blank.","required":False,"type":"textarea","options":[],"archived":False,"section_key":"program_proposals","section_title":"Proposed Program Changes","per_program":False})
    return rows

async def bind_request(request: Request):
    marker=_request.set(request)
    try: yield
    finally: _request.reset(marker)

async def guard_legacy_admin_mutations(request: Request):
    """New projects must pass the versioned approval path, even from old admin URLs."""
    if request.method in {"GET","HEAD","OPTIONS"}:return
    match=re.match(r"/api/admin/sp/projects/([a-zA-Z0-9_-]+)(?:/|$)",request.url.path)
    if not match:return
    # The factory injects the database on this request through its own dependency.
    db=getattr(request.state,"planning_db",None)
    if db is not None and await db.sp_projects.find_one({"project_id":match[1],"guided_service_customer_id":{"$exists":True}},{"_id":1}):
        raise HTTPException(409,"Manage this guided project through its Strategic Planning service workspace so approved versions and board decisions remain protected.")

async def paid_engagement(db, sid):
    row=await db.guided_service_customers.find_one({"workspace_user_id":sid,"service":"strategic-planning"},{"_id":0})
    if not row:return None
    if row.get("payment_status")!="paid":raise HTTPException(402,"This planning service has not been paid for.")
    request=_request.get()
    if request is None:raise HTTPException(401,"Administrator login required to facilitate this planning session.")
    try:await authenticate_admin(request,db)
    except HTTPException as exc:
        if exc.status_code not in (401,403):raise
        from service_handover import operator_for_workspace
        await operator_for_workspace(db,request,sid,"strategic-planning")
    return ({"payment_status":"paid","internal_preview":bool(row.get("internal_test"))},
            {"name":row["name"],"email":row["email"],"organization":row["organization"]},
            {"answers":row.get("answers",{})})

async def provision(db,row):
    from guided_services import now, owner_id
    await db.sp_projects.update_one({"guided_service_customer_id":row["customer_id"]},{"$setOnInsert":{
        "project_id":row["customer_id"],"guided_service_customer_id":row["customer_id"],"guided_session_id":owner_id(row),
        "owner_user_id":owner_id(row),"organization_name":row["organization"],"founder_name":row["name"],"founder_email":row["email"],
        "mission":"","planning_period":"Next 12 to 24 months","programs":[],"questionnaire_version":questionnaire.VERSION,
        "status":"Active","internal_preview":bool(row.get("internal_test")),"created_at":now()}},upsert=True)

def form_content(config,group,project):
    sections=[]
    for q in config["question_groups"][group]:
        if q.get("archived"):continue
        key=q.get("section_key") or q["key"];title=q.get("section_title") or TITLES.get(key,q["prompt"])
        programs=project.get("programs") or []
        targets=programs if q.get("per_program") and programs else [None]
        for program in targets:
            sid="program_"+program["id"] if program else key
            heading=program["name"] if program else title
            item=next((x for x in sections if x["key"]==sid),None)
            if item is None:
                item={"key":sid,"title":heading,"subtitle":q.get("help", ""),"questions":[],"program_id":program["id"] if program else ""};sections.append(item)
            item["questions"].append({**copy.deepcopy(q),"id":q["id"]+("__"+program["id"] if program else ""),"type":"multi" if q["type"]=="multiselect" else "short" if q["type"]=="text" else "long" if q["type"]=="textarea" else q["type"],"answer_type":q["type"],"program_id":program["id"] if program else ""})
    return {"questionnaire_version":questionnaire.VERSION,"guided_service":True,"introduction":config["customer_copy"]["planning_form_intro"],"sections":sections,"mission":project.get("mission", ""),"planning_period":project.get("planning_period", "")}

def session_sections(people,saved):
    sections=[]
    for person in people:
        content=person.get("form_snapshot") or {}
        for source in content.get("sections",[]):
            section=next((x for x in sections if x["key"]==source["key"]),None)
            if section is None:
                section={"key":source["key"],"title":source["title"],"subtitle":source.get("subtitle", ""),"ideas":[],"selected_idea_ids":[],"decision_mode":"selected_ideas","allow_keep_current_mission":False,"recommendations":[],"is_action_planning":source["key"]=="action_planning","is_role_planning":source["key"]=="participation","current_context":""};sections.append(section)
            for q in source.get("questions",[]):
                raw=(person.get("response") or {}).get(q["id"],"")
                if isinstance(raw,list):raw="\n".join(raw)
                raw=str(raw).strip()
                chunks=[x.strip(" \t-*•") for x in re.split(r"\n\s*\n|\n(?=\s*[-*•]\s)",raw) if x.strip()]
                for index,text in enumerate(chunks):
                    section["ideas"].append({"idea_id":f"{person['participant_id']}:{q['id']}:{index}","participant_id":person["participant_id"],"participant_name":person.get("name", "Board member"),"question_id":q["id"],"question":q["prompt"],"idea":text,"source_response":raw})
    for extra in saved.get("discussion_sections",[]):
        if not any(s["key"]==extra["key"] for s in sections):
            sections.append({**extra,"ideas":[],"selected_idea_ids":[],"decision_mode":"selected_ideas","allow_keep_current_mission":False,"recommendations":[],"is_action_planning":False,"is_role_planning":False,"current_context":""})
    for section in sections:
        section["ideas"].extend(copy.deepcopy((saved.get("discussion_ideas") or {}).get(section["key"],[])))
        valid={x["idea_id"] for x in section["ideas"]}
        section["selected_idea_ids"]=[x for x in (saved.get("decisions") or {}).get(section["key"],[]) if x in valid]
        section["review_notes"]=(saved.get("review_notes") or {}).get(section["key"],{})
    return sections

def transcript_text(project,value):
    text=str(value or "").strip()
    if project.get("guided_service_customer_id"):
        if len(text)>240000:raise HTTPException(422,"Keep the transcript within 240,000 characters. Save a separate copy of any additional notes.")
        return text
    return text[:60000]

def approved_context(project,plan,session,people):
    areas=copy.deepcopy(plan.get("areas") or [])
    accepted={p["participant_id"]:(p.get("direction_adoption") or {}).get("revision")==session.get("decision_revision") for p in people}
    for area in areas:
        if area["area_key"]=="participation":
            for idea in area.get("agreed_ideas",[]):idea["individual_acceptance_confirmed"]=bool(accepted.get(idea.get("participant_id")))
    return json.dumps({"organization":project["organization_name"],"existing_mission_background_only":project.get("mission", ""),"planning_period":project.get("planning_period", ""),"explicitly_adopted_decisions":areas,"facilitator_notes":session.get("review_notes",{}),"transcript_context_only_not_authority_to_adopt":session.get("transcript", ""),"outstanding_decisions":[a["area"] for a in areas if not a.get("agreed_ideas")],"instruction":"Only explicitly adopted decisions are authoritative. Notes and transcript can clarify their meaning, never introduce rejected or unapproved suggestions. No new costs, responsibilities, targets or deadlines. Unconfirmed personal responsibilities remain proposals."},ensure_ascii=False)

async def submitted_notice(db,project,person):
    from guided_services import settings, context, render, send_message, continuation
    row=await db.guided_service_customers.find_one({"customer_id":project["guided_service_customer_id"]},{"_id":0})
    config,_,_=await settings(db,"strategic-planning")
    msg=render(config["operational_emails"]["response_notice"],{**context(row),"participant_name":person["name"]})
    return await send_message(db,row,"planning-response-"+person["participant_id"],msg,continuation(row,True)+"?participant="+person["participant_id"])

def review_data(project,person,plan):
    version=plan.get("released_version")
    if not version or person.get("review_released_version")!=version or version!=plan.get("plan_version"):raise HTTPException(409,"The approved review version has not been released to you yet.")
    snap=next((v for v in plan.get("versions",[]) if v["version"]==version),None)
    if not snap:raise HTTPException(409,"This review version is not available.")
    vote=person.get("plan_adoption") or {}
    return {"guided_service":True,"organization_name":project["organization_name"],"branding":project.get("branding",{}),"plan_version":version,"display_text":snap["text"],"submitted":vote.get("version")==version,"decision":vote.get("decision", ""),"requested_changes":vote.get("requested_changes", ""),"prefill":{"full_name":person["name"]}}

async def submit_review(db,project,person,plan,payload):
    from guided_services import now
    data=review_data(project,person,plan)
    if payload.plan_version!=data["plan_version"]:raise HTTPException(409,"The plan has changed. Reload the released version before reviewing it.")
    if payload.decision not in {"adopt","request_change"}:raise HTTPException(422,"Adopt this plan or request a change.")
    comment=str(payload.requested_changes).strip()[:10000]
    if payload.decision=="request_change" and not comment:raise HTTPException(422,"Explain the change you are requesting.")
    vote={"version":payload.plan_version,"decision":payload.decision,"requested_changes":comment,"name":person["name"],"submitted_at":now()}
    existing=person.get("plan_adoption") or {}
    if existing.get("version")==vote["version"]:
        if existing.get("decision")==vote["decision"] and existing.get("requested_changes")==comment:return {"status":"submitted"}
        raise HTTPException(409,"Your decision for this version is already recorded. Ask the facilitator to release a revised version if changes are needed.")
    await db.sp_participants.update_one({"participant_id":person["participant_id"]},{"$set":{"plan_adoption":vote,"review_status":"COMPLETED","review_submitted_at":now()},"$push":{"plan_adoption_history":vote}})
    return {"status":"submitted"}

class Participant(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    email:EmailStr
    role:str="Board Member"

def create_guided_planning_router(db):
    from guided_services import admin_record, record_by_token, now, new_id, owner_id, settings, render, context, preview_email, continuation, EmailDraft, send_message
    from workflow_delivery import deliver_once
    from consultation_routes import no_cache
    router=APIRouter(prefix="/api",dependencies=[Depends(no_cache)])
    base="/admin/services/strategic-planning/customers/{ident}/planning"
    public="/services/strategic-planning/customer/{token}/planning"

    async def project_for(row):
        await provision(db,row)
        return await db.sp_projects.find_one({"guided_service_customer_id":row["customer_id"]},{"_id":0})

    async def detail(row,admin=False):
        p=await project_for(row);people=await db.sp_participants.find({"project_id":p["project_id"]},{"_id":0}).to_list(300)
        plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        live=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        out=[]
        for person in people:
            snap=person.get("form_snapshot") or {}
            item={"participant_id":person["participant_id"],"name":person["name"],"role":person.get("role", ""),"status":person["status"],"submitted_at":person.get("submitted_at"),"response":[{"section":s["title"],"question":q["prompt"],"answer":(person.get("response") or {}).get(q["id"],"")} for s in snap.get("sections",[]) for q in s["questions"]] if person.get("status")=="COMPLETED" else [],"plan_adoption":person.get("plan_adoption",{})}
            if admin:item.update({k:person.get(k,"") for k in ("email","form_token","review_token","form_version","review_released_version","direction_adoption")})
            if person.get("role")=="Lead User":item["form_url"]="/strategic-planning-form/"+person["form_token"]
            if live.get("share_token") and (admin or person.get("role")=="Lead User"):item["meeting_url"]="/strategic-session/"+live["share_token"]+"?participant="+person["form_token"]
            out.append(item)
        published=plan.get("final_status")=="Approved"
        result={"project":{k:v for k,v in p.items() if admin or k in {"organization_name","mission","planning_period","programs","planning_meeting","response_deadline","branding"}},"participants":out,"plan":{"status":plan.get("final_status","NONE"),"text":plan.get("final_display_text","") if admin or published else "","version":plan.get("plan_version",0),"released_version":plan.get("released_version",0),"prepared_version":plan.get("prepared_version",0),"finalized_at":plan.get("finalized_at", "")},"session_id":owner_id(row) if admin else ""}
        if admin:result.update({"session":live,"versions":plan.get("versions",[]),"generation_error":plan.get("final_generation_error", ""),"share_url":"/strategic-plan/"+plan["final_share_token"] if published and plan.get("final_share_token") else ""})
        return result

    @router.get(base)
    async def admin_detail(ident:str,request:Request):return await detail(await admin_record(db,"strategic-planning",ident,request,True),True)

    @router.get(public)
    async def customer_detail(token:str):return await detail(await record_by_token(db,"strategic-planning",token,True))

    @router.put(base+"/setup")
    async def setup(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);p=await project_for(row)
        meeting=payload.get("planning_meeting") or {}
        if not all(str(meeting.get(k,"")).strip() for k in ("meeting_date","start_time","timezone_name")):raise HTTPException(422,"Enter the board meeting date, time and time zone.")
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(meeting["timezone_name"]);datetime.fromisoformat(meeting["meeting_date"]+"T"+meeting["start_time"]);datetime.fromisoformat(str(payload["response_deadline"]))
        except (ValueError,KeyError):raise HTTPException(422,"Enter valid meeting and response-deadline details.")
        programs=[];seen=set()
        for program in payload.get("programs",[]):
            ident_value=program.get("id") or new_id()
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",ident_value) or ident_value in seen:raise HTTPException(422,"Keep unique stable program identifiers.")
            name=str(program.get("name","")).strip()[:300]
            if not name:raise HTTPException(422,"Give each existing program a name.")
            seen.add(ident_value);programs.append({"id":ident_value,"name":name,"description":str(program.get("description", ""))[:3000]})
        period=str(payload.get("planning_period","")).strip()[:500]
        if not period:raise HTTPException(422,"Enter the planning period.")
        values={"mission":str(payload.get("mission", ""))[:10000],"planning_period":period,"programs":programs,"planning_meeting":meeting,"response_deadline":str(payload["response_deadline"]),"branding":row.get("branding",{}),"logo_data_url":(row.get("branding") or {}).get("logo_data", ""),"updated_at":now()}
        await db.sp_projects.update_one({"project_id":p["project_id"]},{"$set":values})
        return {"saved":True}

    async def add_person(row,p,payload,group):
        email=str(payload.email).lower();old=await db.sp_participants.find_one({"project_id":p["project_id"],"email":email},{"_id":0})
        if old:return old
        if group=="board" and email==row["email"]:raise HTTPException(409,"This email belongs to the lead user. Prepare their separate form.")
        config,_,version=await settings(db,"strategic-planning");content=form_content(config,group,p)
        if not p.get("planning_meeting") or not p.get("response_deadline"):raise HTTPException(409,"Save organization setup before preparing personal forms.")
        person={"participant_id":new_id(),"project_id":p["project_id"],"name":payload.name,"email":email,"role":"Lead User" if group=="leader" else "Board Member","board_role":payload.role if group=="board" else "","expertise":"","status":"NOT SENT","form_token":secrets.token_urlsafe(32),"review_token":secrets.token_urlsafe(32),"review_status":"NOT SENT","form_version":version,"form_snapshot":content,"questionnaire_version":questionnaire.VERSION,"created_at":now()}
        if group=="leader":
            first={q["key"]:row.get("answers",{}).get(q["id"],"") for q in row.get("question_snapshot",[])}
            keys={q["id"] for s in content["sections"] for q in s["questions"]}
            person["draft_answers"]={k:v for k,v in {"sp24_01":first.get("vision",""),"sp24_02":first.get("goals","")}.items() if k in keys and v}
        await db.sp_participants.insert_one(copy.deepcopy(person))
        await db.sp_forms.update_one({"project_id":p["project_id"]},{"$setOnInsert":{"project_id":p["project_id"],"status":"Approved","content":content,"approved_at":now()}},upsert=True)
        return person

    @router.post(base+"/leader-form")
    async def leader_form(ident:str,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);p=await project_for(row)
        person=await add_person(row,p,Participant(name=row["name"],email=row["email"]),"leader")
        return {"participant_id":person["participant_id"],"url":"/strategic-planning-form/"+person["form_token"]}

    @router.post(base+"/participants",status_code=201)
    async def add_participant(ident:str,payload:Participant,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True)
        return await add_person(row,await project_for(row),payload,"board")

    async def participant(row,pid):
        person=await db.sp_participants.find_one({"project_id":row["customer_id"],"participant_id":pid},{"_id":0})
        if not person:raise HTTPException(404,"Participant not found for this organization.")
        return person

    async def message_for(row,person,kind):
        from consultation_routes import origin
        p=await project_for(row);config,_,_=await settings(db,"strategic-planning")
        if kind not in {"planning_invitation","review_invitation"}:raise HTTPException(422,"Choose a planning or review invitation.")
        if kind=="review_invitation":
            plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};review_data(p,person,plan)
        path="/strategic-plan-review/"+person["review_token"] if kind=="review_invitation" else "/strategic-planning-form/"+person["form_token"]
        link=origin()+path;meeting=p.get("planning_meeting") or {}
        values={**context(row),"participant_name":person["name"],"leader_name":row["name"],"planning_period":p.get("planning_period", ""),"meeting_details":" ".join(str(meeting.get(k, "")) for k in ("meeting_date","start_time","timezone_name")),"response_deadline":p.get("response_deadline", ""),"form_url":link}
        return {**render(config["operational_emails"][kind],values),"url":link,"recipient":person["email"],"expected_payment_status":"paid"}

    @router.post(base+"/participants/{pid}/message-preview")
    async def preview_message(ident:str,pid:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);msg=await message_for(row,await participant(row,pid),payload.get("kind","planning_invitation"));return {**msg,"html":preview_email(msg,msg["url"])}

    @router.post(base+"/participants/{pid}/message-send")
    async def send_invitation(ident:str,pid:str,payload:EmailDraft,request:Request,kind:str="planning_invitation"):
        row=await admin_record(db,"strategic-planning",ident,request,True);person=await participant(row,pid);prepared=await message_for(row,person,kind)
        if not payload.approved:raise HTTPException(409,"Review and approve the message before sending.")
        from guided_services import email_text
        result=await deliver_once(db,owner_id(row),f"planning-{kind}-{pid}-{payload.request_id}",person["email"],payload.subject,email_text(payload.model_dump()),prepared["url"],cta_label=payload.cta)
        if result["status"] in {"sent","captured"}:
            await db.sp_participants.update_one({"participant_id":pid},{"$set":{"last_invitation_sent_at":now(),"invitation_status":result["status"]}})
            if kind=="planning_invitation":await db.sp_participants.update_one({"participant_id":pid,"status":{"$ne":"COMPLETED"}},{"$set":{"status":"SENT"}})
        return result

    @router.put(base+"/discussion")
    async def discussion_notes(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);p=await project_for(row)
        live=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if live.get("status") in {"REVIEW","COMPLETED"}:raise HTTPException(409,"Return to discussion before editing its decisions.")
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        section=next((s for s in session_sections(people,live) if s["key"]==payload.get("section_key")),None)
        if not section:raise HTTPException(422,"Choose a current planning section.")
        valid={i["idea_id"] for i in section["ideas"]};statuses=payload.get("idea_statuses") or {}
        if set(statuses)-valid or set(statuses.values())-{"pending","rejected","modify","adopted"}:raise HTTPException(422,"Choose valid source ideas and review decisions.")
        value={"notes":str(payload.get("notes", ""))[:15000],"idea_statuses":statuses,"confirmed_owner":str(payload.get("confirmed_owner", ""))[:1000],"owner_agreement_confirmed":payload.get("owner_agreement_confirmed") is True,"updated_at":now()}
        if value["confirmed_owner"] and not value["owner_agreement_confirmed"]:raise HTTPException(422,"Confirm the person's agreement before recording an owner.")
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{f"review_notes.{section['key']}":value}},upsert=True)
        return {"saved":True}

    @router.put(base+"/recording")
    async def recording(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);p=await project_for(row)
        if payload.get("active") and payload.get("consent_confirmed") is not True:raise HTTPException(422,"Confirm the participants' consent before starting transcription.")
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"recording_active":bool(payload.get("active")),"recording_consent_confirmed":bool(payload.get("consent_confirmed")),"recording_updated_at":now()}},upsert=True)
        return {"saved":True}

    @router.post(base+"/subjects")
    async def add_discussion_subject(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True)
        live=await db.sp_sessions.find_one({"project_id":row["customer_id"]},{"_id":0}) or {}
        if live.get("status") in {"REVIEW","COMPLETED"}:raise HTTPException(409,"Return to the discussion before adding a program.")
        name=str(payload.get("name", "")).strip()[:300]
        if not name or payload.get("confirmed") is not True:raise HTTPException(422,"Name and confirm the proposed program to discuss.")
        section={"key":"program_"+new_id(),"title":name,"subtitle":"Review the proposed program and record only the decisions the group explicitly adopts."}
        await db.sp_sessions.update_one({"project_id":row["customer_id"]},{"$push":{"discussion_sections":section},"$set":{"project_id":row["customer_id"],"updated_at":now()}},upsert=True)
        return {"section":section}

    async def plan_for(row):return await db.sp_plans.find_one({"project_id":row["customer_id"]},{"_id":0}) or {}

    @router.put(base+"/plan")
    async def edit_plan(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        text=str(payload.get("text", "")).strip()
        if not text or len(text)>160000:raise HTTPException(422,"Enter the complete plan, up to 160,000 characters.")
        if plan.get("final_status") in {"NONE","Generating"} or not plan.get("areas"):raise HTTPException(409,"Complete the meeting and generate its plan first.")
        if payload.get("expected_version")!=plan.get("plan_version",0):raise HTTPException(409,"The plan changed. Reload before saving.")
        if text==plan.get("final_display_text") and plan.get("plan_version"):return {"version":plan["plan_version"]}
        version=plan.get("plan_version",0)+1
        history=[]
        if not plan.get("versions") and plan.get("final_display_text"):history.append({"version":0,"text":plan["final_display_text"],"status":"Generated draft","saved_at":plan.get("updated_at",now())})
        history.append({"version":version,"text":text,"status":"Draft","saved_at":now()})
        claim=await db.sp_plans.update_one({"project_id":row["customer_id"],"plan_version":plan["plan_version"]} if "plan_version" in plan else {"project_id":row["customer_id"],"plan_version":{"$exists":False}},{"$set":{"final_display_text":text,"final_status":"Draft","plan_version":version,"prepared_version":0,"released_version":0,"updated_at":now()},"$push":{"versions":{"$each":history}}})
        if not claim.modified_count:raise HTTPException(409,"Another edit was saved. Reload the current version.")
        return {"version":version}

    @router.post(base+"/prepare-review")
    async def prepare_review(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if payload.get("approved") is not True or not plan.get("plan_version") or payload.get("version")!=plan["plan_version"]:raise HTTPException(409,"Save and approve this exact plan version before preparing board review.")
        await db.sp_plans.update_one({"project_id":row["customer_id"],"plan_version":payload["version"]},{"$set":{"prepared_version":payload["version"],"review_prepared_at":now()}})
        people=await db.sp_participants.find({"project_id":row["customer_id"]},{"_id":0}).to_list(300)
        return {"version":payload["version"],"links":[{"name":p["name"],"url":"/strategic-plan-review/"+p["review_token"]} for p in people]}

    @router.post(base+"/release-review")
    async def release_review(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if payload.get("confirmed") is not True or not plan.get("prepared_version") or plan.get("prepared_version")!=plan.get("plan_version") or payload.get("version")!=plan["plan_version"]:raise HTTPException(409,"Approve and confirm the current review version before releasing it.")
        await db.sp_plans.update_one({"project_id":row["customer_id"],"plan_version":payload["version"]},{"$set":{"released_version":payload["version"],"review_released_at":now()}})
        await db.sp_participants.update_many({"project_id":row["customer_id"]},{"$set":{"review_released_version":payload["version"]}})
        return {"released":True,"version":payload["version"]}

    @router.post(base+"/finalize")
    async def finalize(ident:str,payload:dict,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if payload.get("organization_approval_confirmed") is not True:raise HTTPException(409,"Confirm the applicable organizational approval before finalizing.")
        version=plan.get("plan_version")
        if not version or version!=plan.get("released_version") or payload.get("version")!=version:raise HTTPException(409,"Release the current version for review first.")
        people=await db.sp_participants.find({"project_id":row["customer_id"]},{"_id":0}).to_list(300)
        if not people or any((p.get("plan_adoption") or {}).get("version")!=version or (p.get("plan_adoption") or {}).get("decision")!="adopt" for p in people):raise HTTPException(409,"Every participating reviewer must adopt this version. Resolve requested changes before finalizing.")
        token=plan.get("final_share_token") or secrets.token_urlsafe(32)
        await db.sp_plans.update_one({"project_id":row["customer_id"],"plan_version":version,"released_version":version},{"$set":{"final_status":"Approved","finalized_at":now(),"organization_approval_confirmed_at":now(),"final_share_token":token,"adopted_by_count":len(people)}})
        return {"status":"Approved","version":version,"share_url":"/strategic-plan/"+token}

    @router.post(base+"/delivery-preview")
    async def delivery_preview(ident:str,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if plan.get("final_status")!="Approved":raise HTTPException(409,"Finalize the approved plan before delivering it.")
        config,_,_=await settings(db,"strategic-planning");msg=render(config["delivery_email"],context(row))
        return {**msg,"expected_payment_status":"paid","recipient":row["email"],"html":preview_email(msg,continuation(row,True))}

    @router.post(base+"/deliver")
    async def deliver_plan(ident:str,payload:EmailDraft,request:Request):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if not payload.approved or plan.get("final_status")!="Approved":raise HTTPException(409,"Finalize the plan and approve its delivery email.")
        result=await send_message(db,row,"planning-final-delivery-"+str(plan["plan_version"]),payload.model_dump(),continuation(row,True))
        if result["status"] in {"sent","captured"}:await db.guided_service_customers.update_one({"customer_id":ident},{"$set":{"resource_delivery_at":now(),"operator_status":"completed"}})
        return result

    def document(project,text,format):
        branding=project.get("branding") or {};title="Strategic Plan";org=project["organization_name"]
        if format=="pdf":
            from document_renderer import render_document_pdf
            data=render_document_pdf(title=title,org_name=org,body_text=text,branding=branding);mime="application/pdf"
        elif format=="docx":
            from docx import Document
            from docx.shared import Inches, RGBColor
            doc=Document()
            if branding.get("logo_data"):
                from PIL import Image
                logo=Image.open(io.BytesIO(base64.b64decode(branding["logo_data"].split(",")[1])));buffered=io.BytesIO();logo.convert("RGBA").save(buffered,format="PNG");buffered.seek(0)
                doc.add_picture(buffered,width=Inches(1))
            h=doc.add_heading(org+" Strategic Plan",0)
            for run in h.runs:run.font.color.rgb=RGBColor.from_string(branding.get("primary_color","#334155").lstrip("#"))
            doc.add_paragraph(project.get("planning_period", ""))
            for line in text.splitlines():
                if line.startswith("#"):doc.add_heading(line.lstrip("# "),min(3,len(line)-len(line.lstrip("#"))))
                else:doc.add_paragraph(line)
            buf=io.BytesIO();doc.save(buf);data=buf.getvalue();mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif format=="txt":data=text.encode();mime="text/plain"
        else:raise HTTPException(422,"Choose PDF, editable Word or text.")
        return Response(data,media_type=mime,headers={"Content-Disposition":f'attachment; filename="Strategic-Plan.{format}"',"Cache-Control":"no-store","X-Robots-Tag":"noindex, nofollow","Referrer-Policy":"no-referrer"})

    @router.get(base+"/download")
    async def admin_download(ident:str,request:Request,format:str="pdf"):
        row=await admin_record(db,"strategic-planning",ident,request,True);plan=await plan_for(row)
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate the plan first.")
        return document(await project_for(row),plan["final_display_text"],format)

    @router.get(public+"/download")
    async def customer_download(token:str,format:str="pdf"):
        row=await record_by_token(db,"strategic-planning",token,True);plan=await plan_for(row)
        if plan.get("final_status")!="Approved":raise HTTPException(409,"The final plan is not ready yet.")
        return document(await project_for(row),plan["final_display_text"],format)

    @router.get("/guided-planning-final/{token}/download")
    async def shared_download(token:str,format:str="pdf"):
        plan=await db.sp_plans.find_one({"final_share_token":token,"final_status":"Approved"},{"_id":0})
        if not plan:raise HTTPException(404,"The approved plan is not available through this link.")
        p=await db.sp_projects.find_one({"project_id":plan["project_id"],"guided_service_customer_id":{"$exists":True}},{"_id":0})
        if not p:raise HTTPException(404,"Plan not found.")
        return document(p,plan["final_display_text"],format)

    from planning_portfolio_tools import register
    register(router,db,base)
    for route in list(router.routes):
        if route.path.startswith("/api"+base):
            router.add_api_route(route.path.replace("/api"+base,"/services/strategic-planning/operator/{ident}/planning"),route.endpoint,methods=list(route.methods))
    return router
