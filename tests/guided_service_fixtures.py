"""Provider transports for disposable guided-service acceptance, never production."""
import os
import uuid
from types import SimpleNamespace
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SESSIONS={};MESSAGES=[];AI=[]
async def generation(kind,context,instructions=''):
    AI.append({'kind':kind,'context':context,'instructions':instructions})
    if kind in {'recruitment_assessment_profiles','powerhouse_board_blueprint'}:
        return {'priority_roles':[{'role_name':'Education Partnerships Leader','why_this_person_is_important':'Connect the organization with local educators.','how_this_person_can_support':'Develop board-level partnerships using agreed introductions.','what_to_look_for':['Education partnerships experience']} ]}
    if kind=='board_opportunity':return {'headline':'Help Children Access Learning','about_the_organization':'We help children access learning.','who_we_are_looking_for':'Education Partnerships Leader','how_to_apply':'Use the board application.'}
    if kind=='interview_guide':return {'sections':[{'heading':'Explore Their Agreed Contribution','questions':['What motivates your interest in this mission?','Which partnerships could you help develop?','What availability can you realistically offer?']}]}
    return {'sections':[{'heading':kind.replace('_',' ').title(),'content':'Support children through the responsibilities discussed and agreed with the organization. Dates, costs and further commitments require confirmation.'}]}
def install(app,db):
    import ai_service,workspace_routes,reactivation_routes,payment_routes,resend,stripe
    from consultation_routes import SOURCE
    from guided_service_defaults import PRODUCTS,PRICES
    ai_service.generate_structured=generation;workspace_routes.generate_structured=generation;reactivation_routes.generate_structured=generation
    previous_create=stripe.checkout.Session.create;previous_price=payment_routes.resolve_offer_price_id;previous_retrieve=stripe.checkout.Session.retrieve
    def price(env_key,lookup,name,amount):
        if lookup==SOURCE:return previous_price(env_key,lookup,name,amount)
        service=next(k for k,v in PRODUCTS.items() if v==lookup);assert amount==PRICES[service]
        return 'price_fixture_'+service
    def create(**kw):
        if kw['metadata']['offer_source']==SOURCE:return previous_create(**kw)
        service=kw['metadata']['guided_service'];assert kw['metadata']['offer_source']==PRODUCTS[service]
        sid='cs_test_guided_'+uuid.uuid4().hex
        SESSIONS[sid]={'id':sid,'metadata':kw['metadata'],'client_reference_id':kw['client_reference_id'],'amount_subtotal':PRICES[service],'amount_total':PRICES[service],'currency':'usd','status':'open','payment_status':'unpaid','success_url':kw['success_url'],'cancel_url':kw['cancel_url'],'payment_intent':'pi_test_'+uuid.uuid4().hex,'livemode':False}
        return SimpleNamespace(id=sid,url='http://127.0.0.1:8765/__test/guided-checkout/'+sid)
    payment_routes.resolve_offer_price_id=price;stripe.checkout.Session.create=create;stripe.checkout.Session.retrieve=lambda sid:SESSIONS[sid] if sid in SESSIONS else previous_retrieve(sid)
    old_mail=resend.Emails.send_async
    async def mail(params,*args,**kwargs):
        MESSAGES.append(params);return await old_mail(params,*args,**kwargs)
    resend.Emails.send_async=mail
    @app.get('/__test/guided-checkout/{sid}')
    async def checkout(sid:str):
        row=SESSIONS[sid]
        return HTMLResponse(f'<h1>Controlled Stripe checkout: ${row["amount_subtotal"]//100}</h1><form method="post"><button name="result" value="paid">Complete Payment</button><button name="result" value="cancel">Cancel Payment</button></form>')
    @app.post('/__test/guided-checkout/{sid}')
    async def result(sid:str,request:Request):
        row=SESSIONS[sid];form=await request.form()
        if form.get('result')=='paid':row.update(status='complete',payment_status='paid');url=row['success_url'].replace('{CHECKOUT_SESSION_ID}',sid)
        else:url=row['cancel_url']
        return RedirectResponse(url,303)
    @app.post('/__test/guided-work/{ident}')
    async def work(ident:str):
        from guided_workspace import work_tick
        await work_tick(db,app,ident);return {'status':'done'}
