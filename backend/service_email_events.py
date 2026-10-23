"""Verified Resend/Svix events. Provider acceptance is never reported as inbox delivery."""
import base64
import hashlib
import hmac
import json
import os
import time
from fastapi import HTTPException, Request


def verify(body, headers, secret, at=None):
    stamp=headers.get('svix-timestamp','');ident=headers.get('svix-id','')
    try:
        if not ident or abs((at or time.time())-int(stamp))>300:raise ValueError()
        key=base64.b64decode(secret.removeprefix('whsec_'),validate=True)
    except (ValueError,TypeError):raise HTTPException(400,'Invalid email-event signature.')
    expected=base64.b64encode(hmac.new(key,ident.encode()+b'.'+stamp.encode()+b'.'+body,hashlib.sha256).digest()).decode()
    if not any(hmac.compare_digest(signature.removeprefix('v1,'),expected) for signature in headers.get('svix-signature','').split()):raise HTTPException(400,'Invalid email-event signature.')
    return ident


def register_routes(router,db):
    @router.post('/webhooks/service-email')
    async def event(request:Request):
        secret=os.environ.get('RESEND_WEBHOOK_SECRET','')
        if not secret:raise HTTPException(503,'Email delivery events are not configured.')
        raw=await request.body()
        if len(raw)>262144:raise HTTPException(413,'Email event is too large.')
        ident=verify(raw,request.headers,secret)
        try:data=json.loads(raw)
        except (ValueError,TypeError):raise HTTPException(422,'Invalid email event.')
        provider_id=(data.get('data') or {}).get('email_id')
        kind=data.get('type')
        status={'email.delivered':'delivered','email.bounced':'bounced','email.complained':'complained','email.delivery_delayed':'delayed','email.failed':'failed'}.get(kind)
        if not status:return {'received':True}
        existing=await db.workflow_email_deliveries.find_one({'provider_id':provider_id}) if provider_id else None
        if not existing:return {'received':True}
        from guided_services import now
        stamp=data.get('created_at') or now()
        # Signed retries are harmless. A newer event cannot be overwritten by an
        # older delivery notification, and sent remains the outbox idempotency state.
        await db.workflow_email_events.update_one({'_id':ident},{'$setOnInsert':{'provider_id':provider_id,'kind':kind,'created_at':stamp,'received_at':now()}},upsert=True)
        await db.workflow_email_deliveries.update_one({'_id':existing['_id'],'$or':[{'provider_event_at':{'$exists':False}},{'provider_event_at':{'$lte':stamp}}]},{'$set':{'delivery_status':status,'provider_event_at':stamp,**({'delivered_at':stamp} if status=='delivered' else {})}})
        if status in {'bounced','complained'}:
            rows=await db.guided_service_customers.find({'workspace_user_id':existing['user_id']},{'_id':0}).to_list(5)
            for row in rows:
                await db.guided_service_suppressions.update_one({'service':row['service'],'email':row['email']},{'$set':{'reason':status,'suppressed_at':now()}},upsert=True)
        return {'received':True}
