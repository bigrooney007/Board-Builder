"""Review and delivery controls around the existing leadership portfolio template."""
import copy
import httpx
from contextvars import ContextVar

trusted_adapter = ContextVar("planning_portfolio_adapter", default=False)
from fastapi import HTTPException, Request
from fastapi.responses import Response


def register(router, db, base):
    from guided_services import admin_record, now, origin, owner_id
    from document_renderer import render_document_pdf
    from workflow_delivery import deliver_once

    async def context(ident, request):
        customer=await admin_record(db,'strategic-planning',ident,request,True)
        plan=await db.sp_plans.find_one({'project_id':ident},{'_id':0}) or {}
        if plan.get('final_status')!='Approved':raise HTTPException(409,'Finalize the adopted strategic plan before preparing leadership portfolios.')
        return customer,plan

    async def reuse(request, path, body):
        headers={k:v for k,v in request.headers.items() if k.lower() in ('authorization','cookie')}
        marker=trusted_adapter.set(True)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=request.app),base_url='http://planning-internal',timeout=180) as client:
                result=await client.post('/api/guided/strategic-planning/'+path,json=body,headers=headers) if path=='portfolios' else await client.put('/api/guided/strategic-planning/'+path,json=body,headers=headers)
        finally:trusted_adapter.reset(marker)
        if not result.is_success:raise HTTPException(result.status_code,result.json().get('detail','The existing portfolio tool could not finish.'))
        return result.json()

    @router.get(base+'/portfolios')
    async def list_portfolios(ident:str,request:Request):
        customer=await admin_record(db,'strategic-planning',ident,request,True)
        plan=await db.sp_plans.find_one({'project_id':ident},{'_id':0}) or {}
        return {'portfolios':plan.get('leadership_portfolios',[]),'delegates':(plan.get('active_delegation') or {}).get('delegates',[])}

    @router.post(base+'/portfolios/prepare')
    async def prepare(ident:str,payload:dict,request:Request):
        customer,plan=await context(ident,request)
        if payload.get('responsibilities_confirmed') is not True:raise HTTPException(422,'Confirm these responsibilities were agreed by the participating members.')
        delegates=payload.get('delegates') or []
        participants=await db.sp_participants.find({'project_id':ident},{'_id':0}).to_list(300)
        known={p['participant_id']:p for p in participants}
        for person in delegates:
            p=known.get(person.get('participant_id'))
            if not p:raise HTTPException(422,'Choose a participant from this planning project.')
            person.update({'name':p['name'],'email':p['email'],'role':p.get('role','')})
        await reuse(request,'active-delegation/people',{'session_id':owner_id(customer),'delegates':delegates})
        # The current generator keeps tokens; protect approved versions against a
        # blanket regeneration by restoring their exact approved snapshots.
        previous={p['delegation_id']:p for p in plan.get('leadership_portfolios',[])}
        await reuse(request,'portfolios',{'session_id':owner_id(customer)})
        current=await db.sp_plans.find_one({'project_id':ident},{'_id':0})
        rows=[]
        for item in current.get('leadership_portfolios',[]):
            old=previous.get(item['delegation_id'],{})
            if old.get('approved_at') and old.get('responsibilities')==item.get('responsibilities'):item=old
            else:
                item.update({'version':old.get('version',0)+1,'approved_at':'','history':old.get('history',[]), 'updated_at':now()})
                if old.get('text'):item['history']=[*item['history'],{'version':old.get('version',1),'text':old['text'],'approved_at':old.get('approved_at',''),'saved_at':now()}]
            rows.append(item)
        await db.sp_plans.update_one({'project_id':ident},{'$set':{'leadership_portfolios':rows}})
        return {'portfolios':rows}

    async def portfolio(ident,pid,request):
        customer,plan=await context(ident,request)
        rows=copy.deepcopy(plan.get('leadership_portfolios',[]));item=next((p for p in rows if p['delegation_id']==pid),None)
        if not item:raise HTTPException(404,'Portfolio not found for this organization.')
        return customer,rows,item

    @router.put(base+'/portfolios/{pid}')
    async def edit(ident:str,pid:str,payload:dict,request:Request):
        customer,rows,item=await portfolio(ident,pid,request)
        before=copy.deepcopy(rows)
        if payload.get('version')!=item.get('version',1):raise HTTPException(409,'Reload the current portfolio before saving.')
        text=str(payload.get('text','')).strip()
        if not text or len(text)>100000:raise HTTPException(422,'Keep a complete portfolio within the document limit.')
        item['history']=[*item.get('history',[]),{'version':item.get('version',1),'text':item['text'],'approved_at':item.get('approved_at',''),'saved_at':now()}]
        item.update({'text':text,'version':item.get('version',1)+1,'approved_at':'','updated_at':now()})
        result=await db.sp_plans.update_one({'project_id':ident,'leadership_portfolios':before},{'$set':{'leadership_portfolios':rows}})
        if not result.matched_count:raise HTTPException(409,'Another portfolio edit was saved. Reload before continuing.')
        return {'portfolio':item}

    @router.post(base+'/portfolios/{pid}/approve')
    async def approve(ident:str,pid:str,payload:dict,request:Request):
        customer,rows,item=await portfolio(ident,pid,request)
        before=copy.deepcopy(rows)
        if payload.get('confirmed') is not True or payload.get('version')!=item.get('version',1):raise HTTPException(409,'Approve the exact saved portfolio version.')
        item.update({'approved_at':item.get('approved_at') or now(),'approved_text':item['text'],'approved_version':item.get('version',1)})
        result=await db.sp_plans.update_one({'project_id':ident,'leadership_portfolios':before},{'$set':{'leadership_portfolios':rows}})
        if not result.matched_count:raise HTTPException(409,'Another portfolio edit was saved. Reload before continuing.')
        return {'portfolio':item}

    @router.get(base+'/portfolios/{pid}/download')
    async def download(ident:str,pid:str,request:Request):
        customer,rows,item=await portfolio(ident,pid,request)
        if not item.get('approved_at') or item.get('approved_version')!=item.get('version'):raise HTTPException(403,'Approve this portfolio before downloading it.')
        pdf=render_document_pdf(title='Board Member Leadership Portfolio',org_name=customer['organization'],body_text=item['approved_text'],branding=customer.get('branding') or {},prepared_for=item['name'])
        return Response(pdf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="leadership-portfolio.pdf"','Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'})

    @router.post(base+'/portfolios/{pid}/send')
    async def send(ident:str,pid:str,payload:dict,request:Request):
        customer,rows,item=await portfolio(ident,pid,request)
        if not item.get('approved_at') or item.get('approved_version')!=item.get('version'):raise HTTPException(403,'Approve this portfolio before sending it.')
        recipient=customer['email'] if payload.get('recipient')=='leader' else item['email']
        from guided_services import settings,render,context as email_context,email_text
        config,_,_=await settings(db,'strategic-planning');message=render(config['operational_emails']['portfolio_delivery'],{**email_context(customer),'participant_name':item['name']})
        result=await deliver_once(db,owner_id(customer),f"planning-portfolio:{pid}:{item['version']}:{recipient}",recipient,message['subject'],email_text(message),origin()+'/strategic-leadership-portfolio/'+item['token'],cta_label=message['cta'],signature=message.get("signature"))
        if result['status'] in ('sent','captured'):
            item['sent_at']=now();await db.sp_plans.update_one({'project_id':ident},{'$set':{'leadership_portfolios':rows}})
        return result
