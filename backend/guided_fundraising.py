"""Guided Fundraising entry adapter into the existing v7 Game project and tools."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from consultation_routes import no_cache


async def provision(db, row):
    from guided_services import now, owner_id
    values={q['key']:row.get('answers',{}).get(q['id'],'') for q in row['question_snapshot']}
    meeting=values.get('next_board_meeting') or {}
    uid=owner_id(row)
    await db.members.update_one({'user_id':uid},{'$addToSet':{'entitlements':'board_fundraising_game'}})
    await db.game_profiles.update_one({'user_id':uid},{'$setOnInsert':{
        'user_id':uid,'workflow_version':7,'simplified_product':True,'guided_service_customer_id':row['customer_id'],
        'organization':{'name':row['organization'],'mission':values.get('mission',''),'board_member_count':int(float(values.get('board_size') or 0)),'funding_consequences':values.get('funding_consequences','')},
        'primary_user':{'full_name':row['name'],'email':row['email']},'goal':{'amount':float(values.get('fundraising_goal') or 0),'deadline':values.get('fundraising_deadline','')},
        'branding':row.get('branding') or {},'profile_completed':True,'created_at':now()}},upsert=True)
    if meeting:
        await db.game_nights.update_one({'user_id':uid},{'$setOnInsert':{'user_id':uid,'meeting_date':meeting.get('date',''),'start_time':meeting.get('time',''),'timezone':meeting.get('timezone','UTC'),'funding_deadline':values.get('fundraising_deadline',''),'created_at':now()}},upsert=True)


def create_guided_fundraising_router(db):
    from guided_services import admin_record, record_by_token, owner_id
    from guided_workspace import delegated_request
    router=APIRouter(prefix='/api',dependencies=[Depends(no_cache)])
    base='/admin/services/board-fundraising/customers/{ident}/fundraising'

    @router.get(base)
    async def workspace(ident:str,request:Request):
        row=await admin_record(db,'board-fundraising',ident,request,True)
        await provision(db,row)
        response=await delegated_request(request.app,db,row,'GET','game/launch/state')
        return response.json()

    @router.get('/services/board-fundraising/customer/{token}/fundraising')
    async def resources(token:str):
        row=await record_by_token(db,'board-fundraising',token,True);uid=owner_id(row)
        people=await db.game_board_members.find({'user_id':uid,'removed':{'$ne':True}},{'_id':0}).to_list(300)
        responses=[]
        for person in people:
            answer=await db.game_audience_responses.find_one({'board_member_id':person['member_id'],'user_id':uid,'completed':True},{'_id':0})
            if answer:responses.append({'name':person['full_name'],'audiences':answer.get('audiences',{}),'involvement':answer.get('involvement','')})
        strategy=await db.game_strategies.find_one({'user_id':uid,'status':'adopted'},{'_id':0},sort=[('adopted_at',-1)])
        portfolios=await db.board_portfolios.find({'user_id':uid,'workflow_version':7,'leader_approved_at':{'$nin':['',None]}},{'_id':0,'member_name':1,'token':1}).to_list(300)
        return {'responses':responses,'strategy_url':'/strategy/'+strategy['share_token'] if strategy else '', 'strategy_pdf':'/api/fundraising/strategy/'+strategy['share_token']+'/document.pdf' if strategy else '', 'portfolios':portfolios}

    @router.api_route(base+'/tool/{path:path}',methods=['GET','POST','PUT'])
    async def tool(ident:str,path:str,request:Request):
        row=await admin_record(db,'board-fundraising',ident,request,True)
        # Only reuse Game actions; their original ownership and approval checks run.
        import re
        if not re.fullmatch(r'game/[a-zA-Z0-9_./-]{1,250}',path) or '..' in path:raise HTTPException(403,'This tool is outside Board Fundraising.')
        response=await delegated_request(request.app,db,row,request.method,path,await request.json() if request.method!='GET' else None,request.url.query)
        return Response(response.content,response.status_code,media_type=response.headers.get('content-type','application/json'),headers={'Cache-Control':'no-store',**({'Content-Disposition':response.headers['content-disposition']} if 'content-disposition' in response.headers else {})})

    for route in list(router.routes):
        if route.path.startswith('/api'+base):
            router.add_api_route(route.path.replace('/api'+base,'/services/board-fundraising/operator/{ident}/fundraising'),route.endpoint,methods=list(route.methods))
    return router
