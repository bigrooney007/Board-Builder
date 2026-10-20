"""Versioned service configuration, free submissions, paid handoff and durable email scheduling.

Only services in ACTIVE_SERVICES enter this flow. Existing purchases and product
records are never migrated. Material/campaign work delegates to the original tools.
"""
import asyncio
import copy
import hashlib
import json
import logging
import math
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import jwt
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from auth_service import authenticate_admin
from consultation_routes import no_cache, origin, safe_url
from guided_service_defaults import ACTIVE_SERVICES, FLOW_VERSION, NAMES, PRICES, PRODUCTS, defaults
from workflow_delivery import deliver_once

logger = logging.getLogger(__name__)
VARIABLES = {"first_name", "name", "organization", "service_name", "price", "mission", "organization_context", "recommendation_update", "continuation_message", "continuation_url", "payment_url", "video_url", "applicant_name", "participant_name", "leader_name", "agreed_purpose", "form_url", "decision", "responsibilities", "interview_details", "planning_period", "meeting_details", "response_deadline"}

def now(): return datetime.now(timezone.utc).isoformat()
def new_id(): return str(uuid.uuid4())
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def owner_id(row): return row["workspace_user_id"]
def check_service(service, active=False):
    if service not in NAMES: raise HTTPException(404, "Service not found.")
    if active and service not in ACTIVE_SERVICES: raise HTTPException(409, "This service continues through its existing customer journey.")

async def settings(db, service, draft=False):
    check_service(service)
    saved = await db.guided_service_settings.find_one({"service": service}, {"_id": 0}) or {}
    def merge(base, value):
        if isinstance(base,dict) and isinstance(value,dict):return {key:merge(default,value.get(key,default)) for key,default in base.items()}
        return copy.deepcopy(value)
    return merge(defaults(service),saved.get("draft" if draft else "published") or {}), saved.get("revision", 0), saved.get("version", "initial")

def validate_questions(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100: raise HTTPException(422, "Keep at least one question in this group.")
    seen=set()
    for q in rows:
        if not isinstance(q, dict) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", str(q.get("id", ""))) or q["id"] in seen: raise HTTPException(422, "Every question needs a unique stable identifier.")
        seen.add(q["id"])
        if q.get("type") not in {"text", "textarea", "number", "date", "select", "multiselect"}: raise HTTPException(422, "Choose a supported answer format.")
        if not isinstance(q.get("prompt"), str) or not q["prompt"].strip() or len(q["prompt"])>4000: raise HTTPException(422, "Every question needs its wording.")
        if not isinstance(q.get("help", ""), str) or len(q.get("help", ""))>6000: raise HTTPException(422, "Question instructions are too long.")
        if not isinstance(q.get("required"), bool) or not isinstance(q.get("archived"), bool): raise HTTPException(422, "Question required and archive settings must be true or false.")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", str(q.get("key", ""))): raise HTTPException(422, "Keep a stable answer key.")
        if not isinstance(q.get("options", []), list) or len(q.get("options", []))>100 or any(not isinstance(x,str) or len(x)>500 for x in q.get("options", [])): raise HTTPException(422, "Invalid answer options.")
        if q["type"] in {"select","multiselect"} and not q.get("options"): raise HTTPException(422,"Add the available answer choices.")
    if not any(not q.get("archived") for q in rows): raise HTTPException(422, "Keep at least one published question.")

def validate_config(service, payload):
    expected=defaults(service)
    if not isinstance(payload,dict) or set(payload)!=set(expected): raise HTTPException(422,"Reload the settings before saving. Some fields are missing or unsupported.")
    if set(payload["question_groups"])!=set(expected["question_groups"]): raise HTTPException(422,"Keep the service's independent question groups.")
    for rows in payload["question_groups"].values(): validate_questions(rows)
    if service=="strategic-planning":
        for group in ("leader","board"):
            for q in payload["question_groups"][group]:
                if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",str(q.get("section_key", ""))) or not str(q.get("section_title", "")).strip() or type(q.get("per_program")) is not bool:raise HTTPException(422,"Keep stable planning section identifiers, titles and program settings.")
    if not safe_url(payload["booking_url"],calendly=True): raise HTTPException(422,"Use a valid secure Calendly URL.")
    if not isinstance(payload["sequence_paused"],bool): raise HTTPException(422,"Invalid sequence setting.")
    if not isinstance(payload["followups"],list) or len(payload["followups"])!=5: raise HTTPException(422,"Keep the five independently editable follow-up messages.")
    if set(payload["operational_emails"])!=set(expected["operational_emails"]):raise HTTPException(422,"Keep the service's operational email templates.")
    for template in [payload["first_email"],payload["video_email"],payload["paid_email"],payload["delivery_email"],*payload["followups"],*payload["operational_emails"].values()]:
        for key in ("subject","headline","body","cta","support","signature"):
            value=template.get(key)
            if not isinstance(value,str) or len(value)>18000 or (key in {"subject","body","cta"} and not value.strip()): raise HTTPException(422,"Email subject, message and button text are required.")
            if set(re.findall(r"{{\s*([a-z_]+)\s*}}",value))-VARIABLES: raise HTTPException(422,"An email contains an unsupported personalization variable.")
        if not isinstance(template.get("enabled"),bool): raise HTTPException(422,"Invalid email enabled setting.")
    for key in ("delay_minutes",):
        if type(payload["first_email"].get(key)) is not int or not 0<=payload["first_email"][key]<=525600: raise HTTPException(422,"Choose a valid first-email delay in minutes.")
    for item in payload["followups"]:
        if type(item.get("after_previous_minutes")) is not int or not 1<=item["after_previous_minutes"]<=525600: raise HTTPException(422,"Choose a positive follow-up interval in minutes.")
    landing=payload["landing"]
    if not isinstance(landing,dict) or set(landing)!=set(expected["landing"]):raise HTTPException(422,"Keep the editable landing page fields.")
    for key,value in landing.items():
        if key=="steps":
            if not isinstance(value,list) or not 1<=len(value)<=20 or any(not isinstance(step,list) or len(step)!=3 or any(not isinstance(v,str) or len(v)>10000 for v in step) for step in value):raise HTTPException(422,"Keep complete numbered landing-page steps.")
        elif key=="outcomes":
            if not isinstance(value,list) or len(value)>30 or any(not isinstance(v,str) or len(v)>10000 for v in value):raise HTTPException(422,"Invalid landing-page outcomes.")
        elif not isinstance(value,str) or len(value)>10000:raise HTTPException(422,"Invalid landing page wording.")
    if service=="board-recommitment":
        form=payload.get("participant_form")
        if not isinstance(form,dict) or set(form)!=set(expected["participant_form"]):raise HTTPException(422,"Keep the participant form fields and stable decision labels.")
        if set(form["labels"])!={"active","advisory","step_down"} or any(not isinstance(v,str) or not v.strip() or len(v)>1000 for v in form["labels"].values()):raise HTTPException(422,"Keep all three independent commitment decisions.")
        for key in ("title","introduction","decision_prompt","decision_help","thank_you"):
            if not isinstance(form[key],str) or len(form[key])>18000:raise HTTPException(422,"Invalid participant form text.")
        validate_questions(form["questions"])
        for q in form["questions"]:
            if not isinstance(q.get("show_for"),list) or not q["show_for"] or set(q["show_for"])-set(form["labels"]):raise HTTPException(422,"Choose which commitment decisions display each question.")
    return payload

async def record_by_token(db,service,token,paid=False):
    check_service(service,active=True)
    if not 40<=len(token)<=100: raise HTTPException(404,"This private service link was not found.")
    row=await db.guided_service_customers.find_one({"service":service,"token_hash":digest(token)}, {"_id":0})
    if not row: raise HTTPException(404,"This private service link was not found.")
    if paid and row.get("payment_status")!="paid": raise HTTPException(402,"Complete payment before opening this part of your service.")
    return row

async def admin_record(db,service,ident,request,paid=False):
    actor=await authenticate_admin(request,db);check_service(service)
    row=await db.guided_service_customers.find_one({"service":service,"customer_id":ident}, {"_id":0})
    if not row: raise HTTPException(404,"Customer not found for this service.")
    if paid and row.get("payment_status")!="paid": raise HTTPException(402,"This customer's guided service has not been paid for.")
    await db.admin_access_audit.insert_one({"actor":actor["user_id"],"target":ident,"service":service,"action":request.method+" "+request.url.path,"created_at":now()})
    return row

def continuation(row,resources=False):
    stage="resources" if resources else "setup" if row.get("payment_status")=="paid" else "offer"
    return f"{origin()}/services/{row['service']}/{stage}/{row['access_token']}"

def context(row,video_url=""):
    answers=row.get("answers") or {};mapping={q["key"]:answers.get(q["id"],"") for q in row.get("question_snapshot",[])}
    ready=(row.get("analysis") or {}).get("status")=="ready"
    return {"first_name":row.get("name","there").split()[0],"name":row.get("name",""),"organization":row.get("organization",""),"service_name":NAMES[row["service"]],"price":str(PRICES[row["service"]]//100),
        "mission":str(mapping.get("mission","")),"organization_context":"\n".join(str(v) for v in mapping.values())[:2000],
        "recommendation_update":"Based on your answers, we've prepared initial board member recommendations for us to review together. These are desired profiles, rather than candidates who have been found." if ready else "Your answers are saved. We will use the priorities you described to work through the board members your organization needs during your guided session.",
        "continuation_message":"Your payment is already confirmed. Use your continuation link to return to the next step of your service." if row.get("payment_status")=="paid" else f"When you are ready to begin the guided {NAMES[row['service']]} service, use your personal continuation link below.",
        "continuation_url":continuation(row),"payment_url":continuation(row),"video_url":video_url}

def render(template,values):
    return {key:re.sub(r"{{\s*([a-z_]+)\s*}}",lambda match:values.get(match[1],""),str(template.get(key,""))) for key in ("subject","headline","body","cta","support","signature")}

def email_text(message): return "\n\n".join(message[k] for k in ("headline","body","support","signature") if message.get(k))

def preview_email(message,link,secondary=None):
    extra=''.join(f'<p><a href="{escape(x["url"],quote=True)}">{escape(x["label"])}</a></p>' for x in secondary or [])
    return '<div style="max-width:640px;margin:auto;font-family:Arial;line-height:1.7;text-align:center">'+escape(email_text(message)).replace('\n','<br>')+extra+f'<p><a href="{escape(link,quote=True)}">{escape(message["cta"])}</a></p></div>'

async def suppressed(db,row):
    if row.get("unsubscribed") or row.get("suppressed") or row.get("sequence_stopped"): return True
    email=row["email"]
    for collection in (db.nurture_contacts,db.nonprofit_contacts):
        contact=await collection.find_one({"email":email},{"_id":0}) or {}
        if contact.get("unsubscribed") or contact.get("unsubscribed_at") or contact.get("suppressed") or contact.get("status","").lower() in {"unsubscribed","suppressed","bounced","complained"}: return True
    return bool(await db.guided_service_suppressions.find_one({"service":row["service"],"email":email}))

async def send_message(db,row,key,message,link=None,*,promotional=False,secondary=None):
    if promotional:
        row=await db.guided_service_customers.find_one({"customer_id":row["customer_id"]},{"_id":0}) or row
        if row.get("payment_status")=="paid" or await suppressed(db,row):return {"status":"stopped"}
    url=link or continuation(row)
    result=await deliver_once(db,owner_id(row),key,row["email"],message["subject"],email_text(message),url,
        cta_label=message["cta"],secondary_links=secondary or [],
        unsubscribe_url=f"{origin()}/api/services/{row['service']}/unsubscribe/{row['unsubscribe_token']}" if promotional else None)
    return result

async def prepare_recommendations(db,row):
    if row["service"]!="recruitment": return
    claim=await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"analysis.status":{"$in":["queued","failed","generating"]},"$or":[{"analysis.lock_until":{"$exists":False}},{"analysis.lock_until":{"$lt":now()}}]},
        {"$set":{"analysis.status":"generating","analysis.lock_until":(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()}})
    if not claim.modified_count:return
    try:
        from ai_service import generate_structured
        data={q["key"]:row.get("answers",{}).get(q["id"],"") for q in row["question_snapshot"]}
        instructions=("Apply the existing Board Recruitment framework to this organization's own answers. Identify a balanced set of desired board member profiles, not actual candidates. Compare existing capability, missing expertise, relationships, mission and intended number of new members. Do not duplicate strengths already covered without a supplied reason. Explain role_name, why_this_person_is_important, how_this_person_can_support and what_to_look_for. Do not invent organization details or claim a person has been found. Respect an explicitly supplied recruitment count; when uncertain, recommend a small practical set. Only draft recommendations, never approved decisions.")
        generated=await generate_structured("recruitment_assessment_profiles",json.dumps({"organization":row["organization"],"answers":data}),instructions)
        if not isinstance(generated,dict) or not isinstance(generated.get("priority_roles"),list) or not generated["priority_roles"]:raise ValueError("No board member profiles were returned")
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"profiles_approved":{"$ne":True}},{"$set":{"recommendations":generated["priority_roles"],"analysis":{"status":"ready","completed_at":now()},"updated_at":now()}})
    except Exception as exc:
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$set":{"analysis":{"status":"failed","error":"Recommendations could not be prepared. Review the submission and retry.","lock_until":(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()},"updated_at":now()},"$inc":{"analysis_attempts":1}})
        logger.warning("Guided recruitment analysis will retry: %s",type(exc).__name__)

async def automation_tick(db,at=None,only_id=None):
    at=at or datetime.now(timezone.utc)
    query={"service":{"$in":list(ACTIVE_SERVICES)},"submitted_at":{"$exists":True}}
    if only_id:query["customer_id"]=only_id
    rows=await db.guided_service_customers.find(query, {"_id":0}).sort("automation_checked_at",1).limit(200).to_list(200)
    for row in rows:
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$set":{"automation_checked_at":at.isoformat()}})
        if row.get("payment_status")=="pending" and row.get("session_id"):
            try:row=await confirm_payment(db,row)
            except HTTPException:pass
        if row.get("payment_status")=="paid":
            await provision_workspace(db,row)
            config,_,_=await settings(db,row["service"])
            await send_message(db,row,"guided-payment-confirmed",render(config["paid_email"],context(row)))
            continue
        config,_,_=await settings(db,row["service"])
        if config["sequence_paused"] or row.get("sequence_paused") or await suppressed(db,row):continue
        first=row.get("first_email_sent_at")
        if not first:
            due=datetime.fromisoformat(row["submitted_at"])+timedelta(minutes=config["first_email"]["delay_minutes"])
            if at<due or not config["first_email"]["enabled"]:continue
            result=await send_message(db,row,"guided-first-invitation",render(config["first_email"],context(row)),promotional=True)
            if result["status"] in {"sent","captured"}:
                await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"first_email_sent_at":{"$exists":False}},{"$set":{"first_email_sent_at":at.isoformat(),"followup_previous_at":at.isoformat(),"followup_index":0}})
        else:
            index=row.get("followup_index",0)
            if index>=5:continue
            message=config["followups"][index]
            if not message["enabled"]:
                await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"followup_index":index},{"$inc":{"followup_index":1}});continue
            due=datetime.fromisoformat(row.get("followup_previous_at") or first)+timedelta(minutes=message["after_previous_minutes"])
            if at<due:continue
            # Re-read immediately before sending so payment/unsubscribe wins the race.
            fresh=await db.guided_service_customers.find_one({"customer_id":row["customer_id"]},{"_id":0})
            result=await send_message(db,fresh,f"guided-followup-{index+1}",render(message,context(fresh)),promotional=True)
            if result["status"] in {"sent","captured"}:
                await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"followup_index":index},{"$inc":{"followup_index":1},"$set":{"followup_previous_at":at.isoformat()}})
    failed_query={"user_id":{"$regex":"^(guided-service-|admin-dashboard-preview-guided-)"},"status":{"$in":["pending","failed","sending"]}}
    if only_id:
        sample=await db.guided_service_customers.find_one({"customer_id":only_id},{"_id":0})
        failed_query["user_id"]=owner_id(sample) if sample else "no-such-workspace"
    failed=await db.workflow_email_deliveries.find(failed_query,{"_id":0}).limit(100).to_list(100)
    for item in failed:
        if item.get("unsubscribe_url"):continue
        # Promotional messages are retried through the stop-condition-aware sequence above.
        if item["event_key"].startswith(("guided-first-","guided-followup-","guided-video-")):continue
        await deliver_once(db,item["user_id"],item["event_key"],item["recipient"],item["subject"],item["text"],item["link"],cta_label=item.get("cta_label","OPEN YOUR RESOURCE"),secondary_links=item.get("secondary_links") or [])

async def service_loop(db):
    while True:
        try:await automation_tick(db)
        except Exception:logger.exception("Guided service automation will retry")
        await asyncio.sleep(60)

async def provision_workspace(db,row):
    if row.get("payment_status")!="paid":raise HTTPException(402,"Payment has not been confirmed.")
    name=row["name"].split(" ",1);uid=owner_id(row)
    alias=row["customer_id"]+"@guided-workspaces.nonprofitboardbuilder.invalid"
    entitlements=["recruitment_self_guided","recruitment_selection_onboarding"] if row["service"]=="recruitment" else ["reactivation_self_guided"] if row["service"]=="board-recommitment" else []
    await db.members.update_one({"user_id":uid},{"$setOnInsert":{"user_id":uid,"email":alias,"notification_email":row["email"],"first_name":name[0],"last_name":name[1] if len(name)>1 else "","entitlements":entitlements,"lead_ids":[row["customer_id"]],"guided_service_workspace":row["service"],"guided_customer_id":row["customer_id"],"lifecycle_optout":True,"admin_notified":True,"internal_dashboard_preview":bool(row.get("internal_test")),"created_at":now()}},upsert=True)
    if row["service"]=="recruitment":await db.members.update_one({"user_id":uid,"guided_service_workspace":"recruitment"},{"$addToSet":{"entitlements":"recruitment_selection_onboarding"}})
    answers={q["key"]:row.get("answers",{}).get(q["id"],"") for q in row["question_snapshot"]}
    data={"organization_name":row["organization"],"mission":answers.get("mission",""),"present_board":answers.get("current_board",""),"desired_board_members_founder_view":answers.get("desired_board_members",""),"priorities":answers.get("board_type",""),"founder_title":"Organization Leader"}
    await db.recruitment_profiles.update_one({"user_id":uid},{"$setOnInsert":{"user_id":uid,"data":data,"confirmed":True,"branding":row.get("branding",{}),"created_at":now()}},upsert=True)
    if row["service"]=="recruitment":
        await db.funnel_leads.update_one({"lead_id":row["customer_id"]},{"$setOnInsert":{"lead_id":row["customer_id"],"member_user_id":uid,"offer_source":"recruitment","lead_source":"founder_guided_recruitment","name":row["name"],"email":row["email"],"organization":row["organization"],"answers":answers,"created_at":now()}},upsert=True)
    elif row["service"]=="board-recommitment":
        await db.board_reactivation_intakes.update_one({"user_id":uid},{"$setOnInsert":{"user_id":uid,"session_id":row.get("session_id") or "guided-"+row["customer_id"],"organization_name":row["organization"],"mission":answers.get("mission",""),"why_recommit":answers.get("why_recommit",""),"board_help_accomplish":answers.get("board_help_accomplish",""),"submitted_at":now()}},upsert=True)
    elif row["service"]=="strategic-planning":
        from guided_planning import provision
        await provision(db,row)

async def confirm_payment(db,row,session_id=None):
    if session_id and session_id!=row.get("session_id"):raise HTTPException(403,"This payment belongs to another record.")
    if row.get("payment_status")=="paid":return row
    if not row.get("session_id"):return row
    try:session=await asyncio.to_thread(stripe.checkout.Session.retrieve,row["session_id"])
    except stripe.StripeError as exc:raise HTTPException(503,"Payment confirmation is temporarily unavailable. Your saved information is safe.") from exc
    meta=session.get("metadata") or {};service=row["service"]
    if meta.get("guided_customer_id")!=row["customer_id"] or meta.get("offer_source")!=PRODUCTS[service] or session.get("client_reference_id")!=row["customer_id"] or session.get("amount_subtotal")!=PRICES[service] or session.get("currency")!="usd" or (session.get("amount_total") or 0)<PRICES[service]:raise HTTPException(409,"The Stripe payment could not be matched to this service.")
    if session.get("payment_status")=="paid":
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"payment_status":{"$ne":"paid"}},{"$set":{"payment_status":"paid","paid_at":now(),"amount_paid":session["amount_total"],"stripe_payment_intent":session.get("payment_intent"),"stripe_livemode":bool(session.get("livemode")),"sequence_stopped":True,"updated_at":now()}})
        row=await db.guided_service_customers.find_one({"customer_id":row["customer_id"]},{"_id":0})
        await provision_workspace(db,row)
        config,_,_=await settings(db,service)
        await send_message(db,row,"guided-payment-confirmed",render(config["paid_email"],context(row)))
    else:
        status="expired" if session.get("status")=="expired" else "pending"
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"payment_status":{"$ne":"paid"}},{"$set":{"payment_status":status,"checkout_status":session.get("status"),"updated_at":now()}})
        row={**row,"payment_status":status,"checkout_status":session.get("status")}
    return row

async def stripe_event(db,event):
    item=event["data"]["object"];meta=item.get("metadata") or {}
    if meta.get("offer_source") not in PRODUCTS.values():return False
    row=await db.guided_service_customers.find_one({"customer_id":meta.get("guided_customer_id")},{"_id":0})
    if row and item.get("id")!=row.get("session_id") and item.get("id") in row.get("checkout_history",[]):return True
    if not row or item.get("id")!=row.get("session_id"):raise HTTPException(503,"The guided service payment record is still being saved.")
    if event["type"] in {"checkout.session.completed","checkout.session.async_payment_succeeded"}:await confirm_payment(db,row)
    elif event["type"] in {"checkout.session.expired","checkout.session.async_payment_failed"}:
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"payment_status":{"$ne":"paid"}},{"$set":{"payment_status":"expired" if event["type"].endswith("expired") else "failed","updated_at":now()}})
    return True

async def calendly_event(db,event):
    # Called only after the existing Calendly endpoint verifies its HMAC and age.
    data=event.get("payload") or {};ident=(data.get("tracking") or {}).get("utm_content")
    row=await db.guided_service_customers.find_one({"customer_id":ident,"payment_status":"paid","branding_saved_at":{"$exists":True},"email":str(data.get("email","")).lower()},{"_id":0})
    if not row:return False
    stamp=event.get("created_at") or data.get("updated_at") or data.get("created_at")
    if not stamp:raise HTTPException(422,"A booking event timestamp is required.")
    status="booked" if event["event"]=="invitee.created" else "cancelled"
    await db.guided_service_customers.update_one({"customer_id":ident,"$or":[{"booking_event_at":{"$exists":False}},{"booking_event_at":{"$lt":stamp}}]},
        {"$set":{"booking_status":status,"booking_event_at":stamp,"calendly_invitee":data.get("uri"),"calendly_event":data.get("event"),"meeting":data.get("scheduled_event") or {},"updated_at":now()}})
    return True

def public_record(row):
    keys=("customer_id","service","name","organization","answers","question_snapshot","question_version","submitted_at","payment_status","booking_status","branding","branding_saved_at","resource_delivery_at","internal_test")
    return {**{key:row.get(key) for key in keys},"amount":PRICES[row["service"]],"currency":"usd","service_name":NAMES[row["service"]]}

class Start(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    request_id:uuid.UUID
    name:str=Field(min_length=1,max_length=200)
    email:EmailStr
    organization:str=Field(min_length=1,max_length=300)

class Answers(BaseModel):
    answers:dict
    submit:bool=False

class ConfigSave(BaseModel):
    config:dict
    revision:int

class Confirm(BaseModel):
    session_id:str=Field(default="",max_length=200)

class Branding(BaseModel):
    logo_data:str=Field(default="",max_length=2500000)
    primary_color:str="#334155"
    secondary_color:str=""

class EmailDraft(BaseModel):
    request_id:uuid.UUID
    subject:str=Field(min_length=1,max_length=500)
    headline:str=""
    body:str=Field(min_length=1,max_length=20000)
    cta:str=Field(min_length=1,max_length=300)
    support:str=""
    signature:str=""
    video_url:str=""
    expected_payment_status:str
    approved:bool=False

async def indexes(db):
    for field in ("customer_id","token_hash","request_id","workspace_user_id"):
        await db.guided_service_customers.create_index(field,unique=True)
    await db.guided_service_settings.create_index("service",unique=True)
    await db.guided_service_versions.create_index([("service",1),("version",1)],unique=True)
    await db.guided_service_limits.create_index("expires_at",expireAfterSeconds=0)

async def rate_limit(db,request,action,limit=15):
    stamp=datetime.now(timezone.utc);bucket=int(stamp.timestamp())//3600
    key=digest((request.client.host if request.client else "unknown")+":"+action+":"+str(bucket))
    await db.guided_service_limits.update_one({"_id":key},{"$inc":{"count":1},"$setOnInsert":{"expires_at":stamp+timedelta(hours=2)}},upsert=True)
    count=await db.guided_service_limits.find_one({"_id":key})
    if count["count"]>limit:raise HTTPException(429,"Please wait before starting another request.")

def create_guided_services_router(db):
    router=APIRouter(prefix="/api",dependencies=[Depends(no_cache)])

    @router.get("/services/{service}/questions")
    async def entry_questions(service:str):
        check_service(service,active=True);config,_,version=await settings(db,service)
        return {"service":service,"name":NAMES[service],"questions":[q for q in config["question_groups"]["entry"] if not q["archived"]],"version":version,"landing":config["landing"]}

    @router.post("/services/{service}/recover")
    async def recover(service:str,payload:dict,request:Request):
        check_service(service,True);await rate_limit(db,request,"recover:"+service,10)
        email=str(payload.get("email","")).strip().lower()
        rows=await db.guided_service_customers.find({"service":service,"email":email,"payment_status":"paid","internal_test":{"$ne":True}},{"_id":0}).limit(5).to_list(5)
        for row in rows:
            config,_,_=await settings(db,service)
            await send_message(db,row,"guided-access-recovery-"+str(int(time.time())//600),render(config["operational_emails"]["access_recovery"],context(row)),secondary=[{"label":"OPEN MY APPROVED RESOURCES","url":continuation(row,True)}])
        return {"message":"If a paid service is associated with that address, we will email your secure access link."}

    @router.post("/services/{service}/start")
    async def start(service:str,payload:Start,request:Request):
        check_service(service,active=True);config,_,version=await settings(db,service)
        if not await db.guided_service_customers.find_one({"request_id":str(payload.request_id)}):await rate_limit(db,request,"start:"+service)
        token=secrets.token_urlsafe(32);ident=new_id();timestamp=now()
        row={"service":service,"customer_id":ident,"request_id":str(payload.request_id),"name":payload.name,"email":str(payload.email).lower(),"organization":payload.organization,"access_token":token,"token_hash":digest(token),"unsubscribe_token":secrets.token_urlsafe(32),"workspace_user_id":"guided-service-"+ident,"flow_version":FLOW_VERSION,"question_snapshot":[q for q in config["question_groups"]["entry"] if not q["archived"]],"question_version":version,"answers":{},"payment_status":"unpaid","booking_status":"not_booked","created_at":timestamp,"updated_at":timestamp}
        await db.guided_service_customers.update_one({"request_id":row["request_id"]},{"$setOnInsert":row},upsert=True)
        saved=await db.guided_service_customers.find_one({"request_id":row["request_id"]},{"_id":0})
        if saved["service"]!=service or saved["email"]!=row["email"] or saved["name"]!=row["name"] or saved["organization"]!=row["organization"]:raise HTTPException(409,"This request was already saved with different contact details. Start a new request.")
        return {"token":saved["access_token"],"record":public_record(saved)}

    @router.get("/services/{service}/customer/{token}")
    async def customer(service:str,token:str):return public_record(await record_by_token(db,service,token))

    @router.put("/services/{service}/customer/{token}/answers")
    async def answers(service:str,token:str,payload:Answers):
        row=await record_by_token(db,service,token)
        if row.get("submitted_at"):raise HTTPException(409,"Your submission is saved. Contact us if it needs a correction.")
        known={q["id"]:q for q in row["question_snapshot"]}
        if any(key not in known for key in payload.answers):raise HTTPException(422,"An answer does not belong to this saved question version.")
        merged={**row.get("answers",{}),**payload.answers}
        for key,value in merged.items():
            if not isinstance(value,(str,int,float,list)) or len(str(value))>18000:raise HTTPException(422,"An answer is too long or has an unsupported format.")
            q=known[key]
            if value not in ("",[]):
                if q["type"]=="number":
                    try:
                        if isinstance(value,(bool,list)) or not math.isfinite(float(value)):raise ValueError()
                    except (ValueError,TypeError):raise HTTPException(422,"Enter a valid number for this question.")
                elif q["type"]=="date":
                    try:datetime.strptime(str(value),"%Y-%m-%d")
                    except ValueError:raise HTTPException(422,"Enter a valid date for this question.")
                elif q["type"]=="multiselect" and not isinstance(value,list):raise HTTPException(422,"Choose the available answers for this question.")
                elif q["type"]!="multiselect" and not isinstance(value,str):raise HTTPException(422,"Enter a text answer for this question.")
            if q["type"] in {"select","multiselect"}:
                values=value if isinstance(value,list) else [value]
                if any(item not in q["options"] for item in values):raise HTTPException(422,"Choose one of the configured options.")
        if payload.submit and any(q["required"] and (merged.get(q["id"]) in (None,"",[]) or isinstance(merged.get(q["id"]),str) and not merged[q["id"]].strip()) for q in known.values()):raise HTTPException(422,"Complete each required question before submitting.")
        updates={"answers":merged,"updated_at":now()}
        if payload.submit:updates.update({"submitted_at":now(),"analysis":{"status":"queued" if service=="recruitment" else "not_required"},"followup_index":0})
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"submitted_at":{"$exists":False}},{"$set":updates})
        return public_record({**row,**updates})

    @router.post("/services/{service}/customer/{token}/checkout")
    async def checkout(service:str,token:str):
        row=await record_by_token(db,service,token)
        if row.get("internal_test"):raise HTTPException(409,"Use the authenticated sample payment action in the admin. This sample cannot create a real charge.")
        if not row.get("submitted_at"):raise HTTPException(409,"Complete your free submission first.")
        if row.get("payment_status")=="paid":return {"resume_url":continuation(row)}
        if row.get("session_id"):
            row=await confirm_payment(db,row)
            if row.get("payment_status")=="paid":return {"resume_url":continuation(row)}
            if row.get("checkout_status")=="open":return {"checkout_url":row["checkout_url"]}
            if row.get("checkout_status")!="expired":raise HTTPException(409,"Your existing payment is processing. Check it before starting another charge.")
        claim=await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"$or":[{"checkout_lock":{"$exists":False}},{"checkout_lock":{"$lt":time.time()-120}}]},{"$set":{"checkout_lock":time.time()}})
        if not claim.modified_count:raise HTTPException(409,"Your secure checkout is opening. Please wait a moment.")
        attempt=row.get("checkout_attempt",0)+1
        try:
            from payment_routes import resolve_offer_price_id
            stripe.api_key=os.environ["STRIPE_SECRET_KEY"]
            price=await asyncio.to_thread(resolve_offer_price_id,"STRIPE_"+PRODUCTS[service].upper()+"_PRICE_ID",PRODUCTS[service],"Guided "+NAMES[service]+" with Rooney",PRICES[service])
            kwargs={"line_items":[{"price":price,"quantity":1}],"mode":"payment","customer_email":row["email"],"client_reference_id":row["customer_id"],"metadata":{"offer_source":PRODUCTS[service],"guided_customer_id":row["customer_id"],"guided_service":service},"success_url":continuation({**row,"payment_status":"paid"})+"?session_id={CHECKOUT_SESSION_ID}","cancel_url":continuation(row)+"?checkout=cancelled","idempotency_key":f"guided:{row['customer_id']}:{attempt}"}
            try:session=await asyncio.to_thread(stripe.checkout.Session.create,**kwargs,managed_payments={"enabled":True})
            except stripe.InvalidRequestError as exc:
                if "managed payments" not in str(exc).lower() and "ineligible" not in str(exc).lower():raise
                session=await asyncio.to_thread(stripe.checkout.Session.create,**{**kwargs,"idempotency_key":kwargs["idempotency_key"]+":standard"},automatic_tax={"enabled":True},billing_address_collection="required")
            await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$set":{"session_id":session.id,"checkout_url":session.url,"checkout_attempt":attempt,"payment_status":"pending","checkout_status":"open","updated_at":now()},"$addToSet":{"checkout_history":session.id},"$unset":{"checkout_lock":""}})
            return {"checkout_url":session.url}
        except (stripe.StripeError,KeyError) as exc:
            await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$unset":{"checkout_lock":""}})
            raise HTTPException(503,"Secure checkout is temporarily unavailable. Please try again.") from exc

    @router.post("/services/{service}/customer/{token}/confirm")
    async def confirm(service:str,token:str,payload:Confirm):return public_record(await confirm_payment(db,await record_by_token(db,service,token),payload.session_id))

    @router.put("/services/{service}/customer/{token}/branding")
    async def branding(service:str,token:str,payload:Branding):
        row=await record_by_token(db,service,token,paid=True)
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",payload.primary_color) or payload.secondary_color and not re.fullmatch(r"#[0-9a-fA-F]{6}",payload.secondary_color):raise HTTPException(422,"Choose a valid six-digit color code.")
        if payload.logo_data:
            import base64,io
            from PIL import Image
            try:
                header,raw=payload.logo_data.split(",",1)
                if header not in {"data:image/png;base64","data:image/jpeg;base64","data:image/webp;base64"}:raise ValueError()
                image=Image.open(io.BytesIO(base64.b64decode(raw,validate=True)));image.verify()
                if image.width*image.height>20000000:raise ValueError()
            except Exception:raise HTTPException(422,"Upload a valid PNG, JPG or WebP logo smaller than 1.8 MB.")
        value=payload.model_dump();await provision_workspace(db,row)
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$set":{"branding":value,"branding_saved_at":now(),"updated_at":now()}})
        await db.recruitment_profiles.update_one({"user_id":owner_id(row)},{"$set":{"branding":value}})
        if service=="board-recommitment":await db.board_reactivation_intakes.update_one({"user_id":owner_id(row)},{"$set":{"logo_data_url":value["logo_data"],"primary_color":value["primary_color"]}})
        return {"status":"saved","branding":value}

    @router.get("/services/{service}/customer/{token}/book")
    async def book(service:str,token:str):
        row=await record_by_token(db,service,token,paid=True)
        if not row.get("branding_saved_at"):raise HTTPException(409,"Save your organization branding before booking.")
        config,_,_=await settings(db,service);parsed=urlparse(config["booking_url"]);params=dict(parse_qsl(parsed.query));params.update({"name":row["name"],"email":row["email"],"utm_content":row["customer_id"]})
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"],"booking_status":"not_booked"},{"$set":{"booking_status":"link_opened","booking_opened_at":now()}})
        return RedirectResponse(urlunparse(parsed._replace(query=urlencode(params))),303,headers={"Referrer-Policy":"no-referrer","Cache-Control":"no-store"})

    @router.api_route("/services/{service}/unsubscribe/{token}",methods=["GET","POST"])
    async def unsubscribe(service:str,token:str,request:Request):
        check_service(service)
        row=await db.guided_service_customers.find_one({"service":service,"unsubscribe_token":token},{"_id":0})
        if not row:raise HTTPException(404,"This unsubscribe link was not found.")
        if request.method=="GET":return HTMLResponse('<main style="max-width:600px;margin:60px auto;font-family:Arial;text-align:center"><h1>Manage Your Follow-up Emails</h1><p>Stop promotional follow-ups for this service. Necessary purchased-service messages will continue.</p><form method="post"><button>Unsubscribe</button></form></main>')
        await db.guided_service_customers.update_one({"customer_id":row["customer_id"]},{"$set":{"unsubscribed":True,"unsubscribed_at":now(),"sequence_stopped":True}})
        await db.guided_service_suppressions.update_one({"service":service,"email":row["email"]},{"$set":{"unsubscribed_at":now()}},upsert=True)
        return HTMLResponse("<h1>You have been unsubscribed from these follow-up emails.</h1>")

    @router.get("/admin/services/{service}/settings")
    async def admin_settings(service:str,request:Request):
        await authenticate_admin(request,db);config,revision,version=await settings(db,service,True)
        return {"config":config,"revision":revision,"version":version,"price":PRICES[service],"active":service in ACTIVE_SERVICES,"name":NAMES[service]}

    @router.put("/admin/services/{service}/draft")
    async def save_draft(service:str,payload:ConfigSave,request:Request):
        actor=await authenticate_admin(request,db);check_service(service);validate_config(service,payload.config)
        existing=await db.guided_service_settings.find_one({"service":service})
        if existing and existing.get("revision",0)!=payload.revision:raise HTTPException(409,"These settings changed in another session. Reload before saving.")
        if not existing:
            await db.guided_service_settings.update_one({"service":service},{"$setOnInsert":{"service":service,"revision":0}},upsert=True)
        result=await db.guided_service_settings.update_one({"service":service,"revision":payload.revision},{"$set":{"draft":payload.config,"updated_by":actor["user_id"],"updated_at":now()},"$inc":{"revision":1}})
        if not result.modified_count:raise HTTPException(409,"Reload the latest settings before saving.")
        return {"revision":payload.revision+1,"status":"saved"}

    @router.post("/admin/services/{service}/publish")
    async def publish(service:str,payload:dict,request:Request):
        actor=await authenticate_admin(request,db);config,revision,_=await settings(db,service,True)
        if payload.get("revision")!=revision:raise HTTPException(409,"Save the current draft before publishing.")
        validate_config(service,config);version=new_id()
        await db.guided_service_versions.insert_one({"service":service,"version":version,"config":config,"published_by":actor["user_id"],"published_at":now()})
        result=await db.guided_service_settings.update_one({"service":service,"revision":revision},{"$set":{"published":config,"version":version,"published_at":now()},"$inc":{"revision":1}})
        if not result.modified_count:raise HTTPException(409,"The draft changed before publication. Reload and try again.")
        return {"version":version,"revision":revision+1,"status":"published"}

    @router.get("/admin/services/{service}/customers")
    async def customers(service:str,request:Request,skip:int=0):
        await authenticate_admin(request,db);check_service(service)
        rows=await db.guided_service_customers.find({"service":service},{"_id":0,"access_token":0,"token_hash":0,"unsubscribe_token":0,"checkout_url":0}).sort("created_at",-1).skip(max(0,skip)).limit(50).to_list(50)
        return {"customers":rows,"total":await db.guided_service_customers.count_documents({"service":service})}

    @router.get("/admin/services/{service}/customers/{ident}")
    async def get_customer(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request)
        deliveries=await db.workflow_email_deliveries.find({"user_id":owner_id(row)},{"_id":0,"link":0}).to_list(200)
        clean={k:v for k,v in row.items() if k not in {"access_token","token_hash","unsubscribe_token","checkout_url"}}
        return {"customer":clean,"deliveries":deliveries,"continuation_url":continuation(row),"resources_url":continuation(row,True)}

    @router.put("/admin/services/{service}/customers/{ident}/sequence")
    async def sequence(service:str,ident:str,payload:dict,request:Request):
        await admin_record(db,service,ident,request)
        values={k:bool(v) for k,v in payload.items() if k in {"sequence_paused","sequence_stopped","suppressed"}}
        await db.guided_service_customers.update_one({"customer_id":ident},{"$set":values})
        return {"status":"saved"}

    @router.post("/admin/services/{service}/customers/{ident}/recommendations/retry")
    async def retry_analysis(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request)
        if service!="recruitment" or not row.get("submitted_at") or row.get("profiles_approved"):raise HTTPException(409,"Submitted, unapproved recruitment profiles are required.")
        await db.guided_service_customers.update_one({"customer_id":ident},{"$set":{"analysis":{"status":"queued"},"analysis_attempts":0}})
        return {"status":"queued"}

    @router.post("/admin/services/{service}/email-preview")
    async def email_preview(service:str,payload:dict,request:Request):
        await authenticate_admin(request,db);check_service(service)
        config,_,_=await settings(db,service,True);key=payload.get("template","first_email")
        if key not in {"first_email","video_email","paid_email","delivery_email","followups","operational_emails"}:raise HTTPException(422,"Choose an email template.")
        if key=="followups":
            index=payload.get("index",0)
            if type(index) is not int or not 0<=index<5:raise HTTPException(422,"Choose one of the five follow-ups.")
            template=config["followups"][index]
        elif key=="operational_emails":template=config[key].get(payload.get("name"))
        else:template=config.get(key)
        if not isinstance(template,dict):raise HTTPException(422,"Choose an email template.")
        sample={"customer_id":"sample","service":service,"name":"Sample Leader","organization":"Sample Nonprofit","answers":{"mission":"Support children in our community."},"question_snapshot":[{"id":"mission","key":"mission"}],"access_token":"sample-secure-link","payment_status":"unpaid","analysis":{"status":"ready"}}
        if key in {"paid_email","delivery_email","operational_emails"}:sample["payment_status"]="paid"
        values={**context(sample),"participant_name":"Sample Board Member","leader_name":"Sample Leader","applicant_name":"Sample Applicant","planning_period":"Next 12 to 24 months","meeting_details":"Your agreed meeting date, time and time zone","response_deadline":"Your agreed response deadline","agreed_purpose":"Clarify the contributions your board members can agree to make.","responsibilities":"Only the responsibilities the person has agreed to accept.","interview_details":"Your confirmed interview arrangements.","video_url":"https://www.youtube.com/watch?v=sample"}
        message=render(template,values);return {**message,"html":preview_email(message,continuation(sample)),"sample":True}

    @router.post("/admin/services/{service}/customers/{ident}/video-preview")
    async def video_preview(service:str,ident:str,payload:dict,request:Request):
        row=await admin_record(db,service,ident,request);url=str(payload.get("video_url","")).strip();parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.hostname not in {"youtube.com","www.youtube.com","youtu.be","m.youtube.com"} or not parsed.path.strip("/"):raise HTTPException(422,"Paste a valid HTTPS YouTube video URL.")
        config,_,_=await settings(db,service);message=render(config["video_email"],context(row,url))
        if row.get("payment_status")=="paid":message["cta"]="CONTINUE MY "+NAMES[service].upper()
        return {**message,"video_url":url,"expected_payment_status":row["payment_status"],"html":preview_email(message,continuation(row),[{"label":"WATCH YOUR VIDEO","url":url}])}

    @router.post("/admin/services/{service}/customers/{ident}/video-send")
    async def video_send(service:str,ident:str,payload:EmailDraft,request:Request):
        row=await admin_record(db,service,ident,request)
        if not payload.approved:raise HTTPException(409,"Review and approve this email before sending.")
        if payload.expected_payment_status!=row["payment_status"]:raise HTTPException(409,"The customer's payment status changed. Refresh the video preview before sending.")
        parsed=urlparse(payload.video_url)
        if parsed.scheme!="https" or parsed.hostname not in {"youtube.com","www.youtube.com","youtu.be","m.youtube.com"}:raise HTTPException(422,"Use a valid HTTPS YouTube video URL.")
        if row["payment_status"]!="paid" and await suppressed(db,row):raise HTTPException(409,"This prospect is unsubscribed or suppressed from promotional messages.")
        message=payload.model_dump()
        result=await send_message(db,row,"guided-video-"+str(payload.request_id),message,promotional=row["payment_status"]!="paid",secondary=[{"label":"WATCH YOUR VIDEO","url":payload.video_url}])
        return result

    @router.post("/admin/services/{service}/test-start")
    async def test_start(service:str,request:Request):
        actor=await authenticate_admin(request,db);check_service(service,True);config,_,version=await settings(db,service)
        ident=new_id();token=secrets.token_urlsafe(32)
        row={"customer_id":ident,"request_id":new_id(),"service":service,"flow_version":FLOW_VERSION,"name":"Sample Nonprofit Leader","email":"sample-leader@nonprofitboardbuilder.internal","organization":"Sample Community Organization","access_token":token,"token_hash":digest(token),"unsubscribe_token":secrets.token_urlsafe(32),"workspace_user_id":"admin-dashboard-preview-guided-"+ident,"question_snapshot":[q for q in config["question_groups"]["entry"] if not q["archived"]],"question_version":version,"answers":{},"payment_status":"unpaid","booking_status":"not_booked","internal_test":True,"test_owner":actor["user_id"],"created_at":now(),"updated_at":now()}
        await db.guided_service_customers.insert_one(row.copy())
        return {"customer_id":ident,"url":f"/services/{service}/start?lead={token}","internal_test":True}

    @router.post("/admin/services/{service}/customers/{ident}/test-advance")
    async def test_advance(service:str,ident:str,payload:dict,request:Request):
        row=await admin_record(db,service,ident,request);actor=await authenticate_admin(request,db)
        if not row.get("internal_test") or row.get("test_owner")!=actor["user_id"]:raise HTTPException(403,"Only your own isolated sample can be advanced without a Stripe payment.")
        if payload.get("action")=="pay":
            if not row.get("submitted_at"):raise HTTPException(409,"Complete the actual free questions first.")
            await db.guided_service_customers.update_one({"customer_id":ident},{"$set":{"payment_status":"paid","paid_at":now(),"sequence_stopped":True,"amount_paid":PRICES[service],"test_payment":True}})
            row={**row,"payment_status":"paid"};await provision_workspace(db,row)
        elif payload.get("action")=="run-email":
            if not row.get("submitted_at"):raise HTTPException(409,"Complete the actual free questions first.")
            await db.guided_service_customers.update_one({"customer_id":ident},{"$set":{"submitted_at":(datetime.now(timezone.utc)-timedelta(days=20)).isoformat()}})
            await automation_tick(db,only_id=ident)
        else:raise HTTPException(422,"Choose a supported sample action.")
        return {"url":continuation(row),"internal_test":True}

    return router
