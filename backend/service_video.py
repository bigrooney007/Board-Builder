"""Owner recording preparation for the single, external AutoFundraiser video service.

No Moses dashboard, guessed remote endpoints, or unauthenticated callbacks live
here. A verified adapter is injected only after the central contract is supplied.
NBB remains the authority for its own customer records and email approvals.
"""
import copy
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

MAX_BYTES = 80 * 1024 * 1024

def integration(request):
    adapter = getattr(request.app.state, 'nbb_central_video_adapter', None)
    return adapter if adapter and getattr(adapter, 'contract_verified', False) else None


def summary(row):
    value = copy.deepcopy(row.get('video_followup') or {})
    value.pop('recording_blob_id', None)
    return value


def register_routes(router, db):
    from auth_service import authenticate_admin
    from guided_services import admin_record, now

    @router.get('/admin/video-followups')
    async def videos(request:Request):
        await authenticate_admin(request,db)
        rows=await db.guided_service_customers.find({'video_followup':{'$exists':True}}, {'_id':0,'customer_id':1,'service':1,'name':1,'organization':1,'video_followup':1}).sort('video_followup.updated_at',-1).limit(200).to_list(200)
        return {'integration_connected':bool(integration(request)), 'central_dashboard_url':'https://autofundraiser.com/video-editor', 'dashboard_live_verified':False, 'videos':[{**{k:v for k,v in row.items() if k!='video_followup'},'video':summary(row)} for row in rows]}

    @router.get('/admin/services/{service}/customers/{ident}/video-assignment')
    async def status(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request)
        return {'video':summary(row),'integration_connected':bool(integration(request)), 'connection_note':'The central AutoFundraiser video contract is pending. Recordings remain private and are not sent to customers automatically.' if not integration(request) else ''}

    @router.post('/admin/services/{service}/customers/{ident}/video-recording')
    async def recording(service:str,ident:str,request:Request,file:UploadFile=File(...)):
        row=await admin_record(db,service,ident,request)
        content_type=file.content_type or ''
        if content_type.split(';')[0] not in {'video/webm','video/mp4'}:raise HTTPException(422,'Record a WebM or MP4 video.')
        first=await file.read(131072)
        if not (first.startswith(b'\x1aE\xdf\xa3') or first[4:8]==b'ftyp'):raise HTTPException(422,'This file is not a supported video recording.')
        bucket=AsyncIOMotorGridFSBucket(db,bucket_name='owner_video_staging')
        stream=bucket.open_upload_stream('recording-'+secrets.token_hex(16),metadata={'customer_id':ident,'service':service,'content_type':content_type,'created_at':now()})
        size=0
        try:
            chunk=first
            while chunk:
                size+=len(chunk)
                if size>MAX_BYTES:raise HTTPException(413,'Keep the recording below 80 MB.')
                await stream.write(chunk);chunk=await file.read(131072)
            await stream.close()
        except Exception:
            await stream.abort();raise
        finally:await file.close()
        old=row.get('video_followup') or {}
        assignment={'recording_id':secrets.token_urlsafe(24),'recording_blob_id':stream._id,'content_type':content_type,'size':size,'status':'recorded','created_at':now(),'updated_at':now()}
        # Retain old metadata; never silently erase a recording that may be in editing.
        update={'$set':{'video_followup':assignment}}
        if old:update['$push']={'video_followup_history':old}
        await db.guided_service_customers.update_one({'customer_id':ident},update)
        return {'video':summary({'video_followup':assignment}), 'integration_connected':bool(integration(request))}

    @router.get('/admin/services/{service}/customers/{ident}/video-recording')
    async def download(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request);video=row.get('video_followup') or {}
        if not video.get('recording_blob_id'):raise HTTPException(404,'The original recording is not available.')
        stream=await AsyncIOMotorGridFSBucket(db,bucket_name='owner_video_staging').open_download_stream(video['recording_blob_id'])
        async def chunks():
            try:
                while True:
                    chunk=await stream.read(131072)
                    if not chunk:break
                    yield chunk
            finally:stream.close()
        return StreamingResponse(chunks(),media_type=video['content_type'],headers={'Cache-Control':'no-store','Content-Disposition':'inline; filename="private-recording.webm"','X-Content-Type-Options':'nosniff'})

    @router.post('/admin/services/{service}/customers/{ident}/video-assignment/submit')
    async def submit(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request);adapter=integration(request)
        if not adapter:raise HTTPException(503,'The AutoFundraiser video integration is not connected yet. Your recording is saved. The verified central API contract must be connected before submitting to Moses.')
        video=row.get('video_followup') or {}
        if not video.get('recording_blob_id'):raise HTTPException(409,'Save a recording before submitting it for editing.')
        if video.get('central_assignment_id'):return {'video':summary(row)}
        from quote_personalization import impact_answer
        # Adapter receives only the approved video brief and original recording;
        # never payment details, organization responses or admin credentials.
        task={'source':'nonprofit-board-builder','source_customer_id':ident,'service':service,'recording_id':video['recording_id'],'brief':{'name':row['name'],'organization':row['organization'],'desired_outcome':impact_answer(row)},'recording_blob_id':video['recording_blob_id'],'idempotency_key':'nbb-video-'+video['recording_id']}
        result=await adapter.submit(task,db)
        if not isinstance(result,dict) or not result.get('assignment_id'):raise HTTPException(502,'The central video service did not confirm an assignment. Your recording remains saved.')
        updates={'video_followup.central_assignment_id':str(result['assignment_id']),'video_followup.status':'submitted','video_followup.updated_at':now()}
        await db.guided_service_customers.update_one({'customer_id':ident,'video_followup.recording_id':video['recording_id']},{'$set':updates})
        return {'status':'submitted'}

    @router.post('/admin/services/{service}/customers/{ident}/video-assignment/refresh')
    async def refresh(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request);adapter=integration(request);video=row.get('video_followup') or {}
        if not adapter or not video.get('central_assignment_id'):raise HTTPException(409,'No connected central assignment is available yet.')
        result=await adapter.status(video['central_assignment_id'])
        if result.get('source_customer_id')!=ident or result.get('service')!=service:raise HTTPException(409,'The returned video belongs to another source record.')
        if result.get('status') not in {'submitted','editing','revision_requested','ready'}:raise HTTPException(502,'The central service returned an unsupported status.')
        updates={'video_followup.status':result['status'],'video_followup.updated_at':now()}
        if result['status']=='ready':
            parsed=urlparse(result.get('youtube_url',''))
            if parsed.scheme!='https' or parsed.hostname not in {'youtube.com','www.youtube.com','youtu.be','m.youtube.com'}:raise HTTPException(422,'The completed video needs a verified YouTube URL.')
            if not isinstance(result.get('transcript'),str) or len(result['transcript'])>240000:raise HTTPException(422,'The returned transcript is invalid.')
            updates.update({'video_followup.youtube_url':result['youtube_url'],'video_followup.transcript':result['transcript'],'video_followup.ready_at':now()})
        await db.guided_service_customers.update_one({'customer_id':ident,'video_followup.recording_id':video['recording_id']},{'$set':updates})
        return {'status':result['status']}

    @router.post('/admin/services/{service}/customers/{ident}/video-assignment/review')
    async def review(service:str,ident:str,payload:dict,request:Request):
        row=await admin_record(db,service,ident,request);video=row.get('video_followup') or {}
        if video.get('status') not in {'ready','approved'}:raise HTTPException(409,'A completed video is required before owner review.')
        action=payload.get('action')
        if action=='revision':
            adapter=integration(request)
            if not adapter:raise HTTPException(503,'The central video connection is unavailable.')
            note=str(payload.get('notes','')).strip()
            if not note:raise HTTPException(422,'Explain the revision you want.')
            await adapter.request_revision(video['central_assignment_id'],note[:10000])
        elif action!='approve':raise HTTPException(422,'Approve the video or request a revision.')
        await db.guided_service_customers.update_one({'customer_id':ident,'video_followup.recording_id':video['recording_id']},{'$set':{'video_followup.status':'approved' if action=='approve' else 'revision_requested','video_followup.approved_at':now() if action=='approve' else '', 'video_followup.updated_at':now()}})
        return {'status':'approved' if action=='approve' else 'revision_requested'}

    @router.delete('/admin/services/{service}/customers/{ident}/video-recording')
    async def delete(service:str,ident:str,request:Request):
        row=await admin_record(db,service,ident,request);video=row.get('video_followup') or {}
        if video.get('status')!='approved' or not video.get('youtube_url'):raise HTTPException(409,'Verify and approve the completed YouTube video before deleting its original recording.')
        if video.get('recording_blob_id'):
            await AsyncIOMotorGridFSBucket(db,bucket_name='owner_video_staging').delete(video['recording_blob_id'])
            await db.guided_service_customers.update_one({'customer_id':ident},{'$unset':{'video_followup.recording_blob_id':''},'$set':{'video_followup.original_deleted_at':now()}})
        return {'status':'deleted','youtube_url':video['youtube_url']}
