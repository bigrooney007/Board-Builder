"""Administrator facilitation and approval using the existing game records."""
import copy
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Request, File, UploadFile
from fastapi.responses import Response
from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from workflow_delivery import deliver_once


def now(): return datetime.now(timezone.utc).isoformat()


def valid_booking(value):
    parsed=urlparse(value)
    return parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password and not any(c.isspace() for c in value)


def edited_sections(original, values):
    from fundraising_strategy_writing import LABELS
    if not isinstance(values,list) or [v.get('key') for v in values]!=[s['key'] for s in original]:
        raise HTTPException(422,'Keep the approved audience and section structure')
    result=[]
    for old,value in zip(original,values):
        text=str(value.get('text') or '').strip()
        title=str(value.get('title') or old['title']).strip()
        if not text or len(text)>80000 or not title or len(title)>500:raise HTTPException(422,'Keep a complete heading and text in every section')
        section={**copy.deepcopy(old),'title':title,'text':text}
        if text!=old['text']:
            blocks=[]
            for line in text.splitlines():
                line=line.strip()
                if not line:continue
                label=line.lstrip('-• ').rstrip(':')
                blocks.append({'kind':'bullet_heading' if label in LABELS.values() else 'body','text':label if label in LABELS.values() else line})
            section['blocks']=blocks
        result.append(section)
    return result


async def deliver_approved(db,strategy):
    from fundraising_launch import content,origin
    owner=await db.members.find_one({'user_id':strategy['user_id']},{'_id':0}) or {}
    booking=(await content(db))['settings']['booking_url']
    guided=await db.guided_service_customers.find_one({'workspace_user_id':strategy['user_id'],'service':'board-fundraising','payment_status':'paid'},{'_id':0})
    if guided:
        from guided_services import settings,render,context,email_text
        config,_,_=await settings(db,'board-fundraising');message=render(config['operational_emails']['strategy_ready'],context(guided))
        return await deliver_once(db,strategy['user_id'],'admin-strategy-approved:'+strategy['strategy_id'],guided['email'],message['subject'],email_text(message),origin()+'/strategy/'+strategy['share_token'],cta_label=message['cta'],secondary_links=[{'label':'Book a Conversation About Your Strategy','url':config['booking_url']}])
    return await deliver_once(db,strategy['user_id'],'admin-strategy-approved:'+strategy['strategy_id'],owner.get('notification_email') or owner.get('email',''),
        "Your Board's Fundraising Strategy Is Ready",
        "Your board's adopted fundraising strategy has been reviewed and is ready to use. Open your strategy to read, download and share it with your board. You can also book a conversation with Rooney to discuss the strategy and its execution.",
        origin()+'/strategy/'+strategy['share_token'],secondary_links=[{'label':'Book a Conversation About Your Strategy','url':booking}])


def create_facilitation_router(db):
    router=APIRouter(prefix='/api')

    async def admin(request,action,target):
        try:actor=await authenticate_admin(request,db)
        except HTTPException as exc:
            if exc.status_code not in (401,403):raise
            from service_handover import operator_record
            customer=await operator_record(db,request,'board-fundraising')
            strategy=await db.game_strategies.find_one({'strategy_id':target,'user_id':customer['workspace_user_id']},{'_id':0})
            if not strategy:raise HTTPException(403,'This strategy belongs to another organization.')
            actor={'user_id':customer['workspace_user_id']}
        await db.admin_access_audit.insert_one({'actor':actor['user_id'],'action':action,'target':target,'created_at':now()})
        return actor

    async def strategy_for(ident):
        row=await db.game_strategies.find_one({'strategy_id':ident,'schema_version':7},{'_id':0})
        if not row:raise HTTPException(404,'This strategy was not found')
        session=await db.group_game_sessions.find_one({'user_id':row['user_id'],'strategy_id':ident,'status':'completed'},{'_id':0})
        if not session:raise HTTPException(409,'End the group meeting before reviewing its final document')
        return row

    @router.get('/admin/fundraising/strategies/{ident}')
    async def read_strategy(ident:str,request:Request):
        await admin(request,'read-strategy-draft',ident)
        row=await strategy_for(ident)
        from fundraising_transcript import source_text
        transcript=await source_text(db,row['user_id'])
        return {'strategy':row,'transcript':transcript}

    @router.put('/admin/fundraising/strategies/{ident}')
    async def save_strategy(ident:str,payload:dict,request:Request):
        actor=await admin(request,'edit-strategy-draft',ident);row=await strategy_for(ident)
        if row['status']!='final_draft':raise HTTPException(409,'This approved strategy is saved and cannot be changed')
        if payload.get('version')!=row['version']:raise HTTPException(409,'Reload the current document before editing')
        clean=edited_sections(row['document_sections'],payload.get('sections'))
        result=await db.game_strategies.update_one({'strategy_id':ident,'status':'final_draft','version':row['version']},{'$set':{
            'document_sections':clean,'document_text':'\n\n'.join(s['title']+'\n'+s['text'] for s in clean),'section_edits':{s['key']:s['text'] for s in clean},
            'admin_saved_at':now(),'admin_saved_by':actor['user_id']},'$inc':{'version':1}})
        if not result.modified_count:raise HTTPException(409,'This document changed. Reload and try again')
        return {'strategy':await strategy_for(ident),'saved':True}

    @router.post('/admin/fundraising/strategies/{ident}/approve')
    async def approve_strategy(ident:str,payload:dict,request:Request):
        actor=await admin(request,'approve-strategy',ident);row=await strategy_for(ident)
        if payload.get('confirmed') is not True or payload.get('version')!=row['version']:raise HTTPException(409,'Confirm the exact current document before delivery')
        if row['status']!='adopted':
            if not row.get('admin_saved_at'):raise HTTPException(409,'Review and save the document before approving it')
            result=await db.game_strategies.update_one({'strategy_id':ident,'status':'final_draft','version':row['version']},{'$set':{'status':'adopted','adopted_at':now(),'approved_by':actor['user_id']}})
            if not result.modified_count:raise HTTPException(409,'The strategy changed. Review it again')
            await db.group_game_sessions.update_one({'strategy_id':ident},{'$set':{'audience_review.phase':'approved'}})
            from fundraising_launch import touch
            await touch(db,row['user_id'],'complete','/game/dashboard')
        row=await strategy_for(ident)
        delivery=await deliver_approved(db,row)
        if delivery['status'] in ('sent','captured'):await db.guided_service_customers.update_one({'workspace_user_id':row['user_id'],'service':'board-fundraising'},{'$set':{'operator_status':'completed','resource_delivery_at':now()}})
        return {'approved':True,'delivery':delivery}

    @router.post('/game/launch/plan-upload')
    async def upload_plan(request:Request,file:UploadFile=File(...)):
        member=await authenticate_member(request,db);require_entitlement(member,{'board_fundraising_game'})
        from fundraising_launch import now as timestamp
        profile=await db.game_profiles.find_one({'user_id':member['user_id'],'workflow_version':7},{'_id':0})
        if not profile:raise HTTPException(409,'Continue your saved game in its existing format')
        data=await file.read(5_000_001)
        name=re.sub(r'[^\w .()-]','_',file.filename or 'fundraising-plan',flags=re.ASCII)[:180]
        if not data or len(data)>5_000_000:raise HTTPException(422,'Upload a plan up to 5 MB')
        ext=name.rsplit('.',1)[-1].lower()
        if ext not in {'pdf','docx','txt'}:raise HTTPException(422,'Use a PDF, DOCX or text document')
        text=''
        try:
            from io import BytesIO
            if ext=='pdf':
                from pypdf import PdfReader
                text='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(data)).pages[:100])
            elif ext=='docx':
                import zipfile
                with zipfile.ZipFile(BytesIO(data)) as archive:
                    if sum(i.file_size for i in archive.infolist())>20_000_000:raise ValueError('Document too large')
                from docx import Document
                text='\n'.join(p.text for p in Document(BytesIO(data)).paragraphs)
            else:text=data.decode('utf-8')
        except Exception as exc:raise HTTPException(422,'This document could not be read. Upload another copy or describe your approach instead') from exc
        await db.game_fundraising_plans.update_one({'user_id':member['user_id']},{'$set':{'filename':name,'data':data,'text':text[:120000],'updated_at':timestamp()}},upsert=True)
        await db.game_profiles.update_one({'user_id':member['user_id']},{'$set':{'organization.plan_filename':name}})
        return {'saved':True,'filename':name}

    @router.get('/game/launch/plan-upload')
    async def read_plan(request:Request):
        member=await authenticate_member(request,db);require_entitlement(member,{'board_fundraising_game'})
        row=await db.game_fundraising_plans.find_one({'user_id':member['user_id']})
        if not row:raise HTTPException(404,'No plan has been uploaded')
        ext=row['filename'].rsplit('.',1)[-1].lower()
        media={'pdf':'application/pdf','txt':'text/plain','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}[ext]
        return Response(bytes(row['data']),media_type=media,headers={'Content-Disposition':'attachment; filename="'+row['filename']+'"','X-Content-Type-Options':'nosniff','X-Robots-Tag':'noindex, nofollow'})

    return router
