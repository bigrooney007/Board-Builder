"""Desktop/mobile acceptance through the actual simplified React pages and APIs."""
import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright, expect
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'

async def main():
    for _ in range(80):
        try:
            with urllib.request.urlopen(BASE+'/__test/session'):break
        except Exception:await asyncio.sleep(.25)
    results=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        for width in (1440,390):
            context=await browser.new_context(viewport={'width':width,'height':1000 if width==1440 else 844},accept_downloads=True,permissions=['clipboard-read','clipboard-write'],record_video_dir=f'test_reports/current-simplified-video-{width}',record_video_size={'width':width,'height':1000 if width==1440 else 844})
            auth=(await (await context.request.get(BASE+'/__test/session')).json())['token']
            response=await context.request.post(BASE+'/api/admin/fundraising/test-start',headers={'Authorization':'Bearer '+auth});assert response.ok,await response.text()
            test=await response.json();
            defaults=json.loads(Path("backend/fundraising_launch_content.json").read_text());reset=await context.request.put(BASE+"/api/admin/fundraising/content",data=defaults,headers={"Authorization":"Bearer "+auth});assert reset.ok,await reset.text()
            page=await context.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(BASE);await page.evaluate('(token)=>localStorage.setItem("memberToken",token)',test['token']);await page.reload()
            await page.get_by_test_id('fundraising-home-page').wait_for()
            await page.get_by_role('heading',name='The Fundraising Game',exact=True).wait_for()
            assert await page.get_by_text('Imagine walking into your next board meeting',exact=False).count()==1
            await expect(page.get_by_role('button',name='Play The Fundraising Game With Your Board',exact=True)).to_have_count(4)
            for slot in ('fundraising-cta-after-explanation','fundraising-cta-after-biography'):
                await page.get_by_test_id(slot).get_by_role('button').click()
                await page.get_by_role('dialog').wait_for()
                await expect(page.get_by_role('dialog').get_by_role('checkbox')).to_have_count(0)
                await page.get_by_role('button',name='Close',exact=True).click()
            assert await page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2')
            await page.screenshot(path=f'test_reports/current-simplified-home-{width}.png',full_page=True)
            results.append({'width':width,'case':'supplied_homepage_and_layout','passed':True})
            await page.get_by_role('button',name='Play The Fundraising Game With Your Board',exact=True).first.click()
            await page.get_by_label('Full name',exact=True).fill('Sample Leader')
            await page.get_by_label('Email address',exact=True).fill('leader@example.org')
            await page.get_by_label('Organization name',exact=True).fill('BrightPath Youth Alliance')
            async with page.expect_response(lambda r:'/api/fundraising/leads' in r.url and r.request.method=='POST') as captured:
                await page.get_by_role('button',name='See How The Fundraising Game Works',exact=True).click()
            saved=await captured.value;assert saved.ok,await saved.text()
            await page.wait_for_url('**/how-the-fundraising-game-works?lead=*')
            await page.get_by_test_id('fundraising-how-page').wait_for()
            await page.get_by_role('heading',name='Get Your Board Members Fundraising By Your Next Board Meeting.',exact=True).wait_for()
            await expect(page.get_by_text('What You\'re Getting for $997',exact=True)).to_be_visible()
            assert await page.get_by_test_id('fundraising-how-page').get_by_text('portfolio',exact=False).count()==0
            await page.get_by_role('button',name='Start The Fundraising Game',exact=True).first.click()
            await page.wait_for_url('**/game/setup')
            await page.get_by_label('Fundraising goal',exact=True).fill('100000')
            await page.get_by_label('Mission statement',exact=True).fill('Help young people enter employment.')
            await page.get_by_label('Annual budget',exact=True).fill('$150,000')
            await page.get_by_label('Organization website',exact=True).fill('https://example.org')
            await page.get_by_label('Who or what community your organization serves',exact=True).fill('Young people seeking employment')
            await page.get_by_role('button',name='Save and Start The Game',exact=True).click()
            await page.wait_for_url('**/play/*')
            await page.get_by_role('button',name='START MY GAME',exact=True).click()
            audience_rows=(('individuals',('Former mentors','Parents of former participants')),('businesses',('Local employers','Professional services businesses')),('grantmakers',('Youth employment foundations','Community foundations')))
            for category,proposed in audience_rows:
                for who in proposed:
                    await page.get_by_role('button',name='YES',exact=True).click()
                    values=[who+' care about youth employment.','Community networks.','Share programme outcomes.','Ask for introductions, develop trust and then invite support.','Fund mentoring places, $500 each.']
                    for index,value in enumerate(values):
                        await expect(page.locator('.guided-question-top span').first).to_contain_text(f'Question {index+1} of 5')
                        await expect(page.get_by_role('textbox',name='Your audience answer')).to_have_count(1)
                        if category=='individuals' and index==2:await expect(page.get_by_role('heading',level=1)).to_contain_text('consistently')
                        if category=='businesses' and index==3:await expect(page.get_by_role('heading',level=1)).to_contain_text('proposal asking for money')
                        if category=='grantmakers' and index==3:await expect(page.get_by_role('heading',level=1)).to_contain_text('not just about writing an application')
                        await page.get_by_role('textbox',name='Your audience answer').fill(value)
                        await page.get_by_role('button',name='NEXT QUESTION' if index<4 else 'SAVE THIS AUDIENCE AND CONTINUE',exact=True).click()
                    await expect(page.get_by_role('heading',level=1)).to_contain_text('recommend')
                await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
            await expect(page.get_by_role('heading',level=1)).to_contain_text('How do you see yourself participating and supporting your organization to reach this fundraising goal?')
            await page.get_by_role('textbox',name='Your personal participation').fill('I can introduce local employers.')
            await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click()
            await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
            await page.wait_for_url('**/game/setup')
            await page.get_by_label('Board meeting date',exact=True).fill('2026-12-01')
            await page.get_by_label('Meeting start time',exact=True).fill('16:00')
            await page.get_by_label('Time zone',exact=True).fill('Europe/London')
            await page.get_by_role('button',name='Save Meeting and Invite My Board',exact=True).click()
            await page.get_by_role('heading',name='Invite your board members',exact=True).wait_for()
            results.append({'width':width,'case':'contact_payment_setup_five_questions_before_meeting','passed':True})
            await page.get_by_role('button',name='Open My Workspace',exact=True).click()
            await page.wait_for_url('**/game/dashboard')
            await page.get_by_test_id('fundraising-workspace').wait_for()
            await expect(page.get_by_test_id('bfg-board-members-section').get_by_text('Sample Leader',exact=True)).to_have_count(0)
            assert await page.get_by_role('button',name='Download Final Fundraising Strategy',exact=True).is_disabled()
            await expect(page.get_by_role('button',name='Generate Board Portfolios',exact=True)).to_have_count(0)
            await page.screenshot(path=f'test_reports/current-simplified-workspace-{width}.png',full_page=True)
            assert await page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2'), await page.locator('body *').evaluate_all('(rows)=>rows.filter(e=>e.getBoundingClientRect().right>window.innerWidth+2).slice(0,8).map(e=>({tag:e.tagName,css:e.className,text:e.textContent.slice(0,100),width:e.getBoundingClientRect().width}))')
            results.append({'width':width,'case':'real_workspace_locked_outputs_and_responses','passed':True})
            # Sample identities use the current real participant records and forms.
            await page.get_by_role('button',name='Add Three Sample Board Members',exact=True).click()
            await page.get_by_role('link',name="Open Alex Morgan's Personal Game",exact=True).wait_for()
            alex_personal=await page.get_by_role('link',name="Open Alex Morgan's Personal Game",exact=True).get_attribute("href")
            member_token=await page.evaluate("localStorage.getItem('memberToken')")
            member_headers={'Authorization':'Bearer '+member_token}
            await page.add_init_script("""window.SpeechRecognition=class {
              start(){if(this.onresult){const row=[{transcript:'Alex agrees to introduce interested employers.'}];row.isFinal=true;this.onresult({resultIndex:0,results:[row]})}}
              stop(){if(this.onend)this.onend()}
            };window.__microphoneRequests=0;
            Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{
              window.__microphoneRequests++;
              if(window.__denyMicrophoneOnce){window.__denyMicrophoneOnce=false;throw new DOMException('Denied for this test','NotAllowedError')}
              return {getTracks:()=>[{stop:()=>{}}]};
            }}});""")
            await page.get_by_role('button',name='Start The Group Game',exact=True).click()
            await page.wait_for_url('**/game/group')
            review=page.get_by_test_id('bfg-audience-group-review');await review.wait_for()
            group_response=await context.request.get(BASE+'/api/game/group/session',headers=member_headers);assert group_response.ok
            group=await group_response.json();group_token=group['session']['token']
            participant_contexts=[];participant_pages=[]
            microphone=page.get_by_role('dialog',name='Enable your meeting microphone')
            await microphone.wait_for()
            if width==390:
                await page.evaluate('window.__denyMicrophoneOnce=true')
                await microphone.get_by_role('button',name='Enable Meeting Microphone',exact=True).click()
                await expect(microphone.get_by_role('alert')).to_contain_text('Microphone access was not enabled')
                denied_state=await (await context.request.get(BASE+'/api/game/group/session',headers=member_headers)).json()
                assert not denied_state['session'].get('transcript_consent')
            await microphone.get_by_role('button',name='Enable Meeting Microphone',exact=True).click()
            await page.get_by_test_id('bfg-recording-state').wait_for()
            assert await page.evaluate('window.__microphoneRequests')==(2 if width==390 else 1)
            await review.get_by_role('button',name='START GROUP REVIEW',exact=True).click()
            await page.get_by_test_id('private-facilitation-guide').wait_for()
            for name in ('Alex','Taylor','Jordan'):
                pc=await browser.new_context(viewport={'width':width,'height':844});pp=await pc.new_page()
                if name=='Alex':
                    await pp.goto(BASE+alex_personal)
                    await pp.get_by_role('heading',name='Your Fundraising Ideas Are Saved',exact=True).wait_for()
                    await expect(pp.get_by_text('We are grateful for your contribution.',exact=False)).to_be_visible()
                    await expect(pp.get_by_role('button',name='CONTINUE TO MEETING SETUP',exact=True)).to_have_count(0)
                await pp.goto(BASE+'/group-game/'+group_token)
                await pp.get_by_role('button',name=name,exact=True).click()
                await pp.get_by_role('button',name='Join The Game',exact=True).click()
                await pp.get_by_role('heading',name='Our Group Fundraising Discussion',exact=True).wait_for()
                assert await pp.get_by_test_id('private-facilitation-guide').count()==0
                assert await pp.get_by_role('button',name='Approve Audience',exact=True).count()==0
                participant_contexts.append(pc);participant_pages.append(pp)
            await page.get_by_test_id('bfg-recording-state').wait_for()
            async with page.expect_response(lambda r:'/game/meeting/recording/finish' in r.url) as recorded:
                await page.get_by_test_id('bfg-recording-finish').click()
            assert (await recorded.value).ok
            if width==390:
                await page.reload()
                resumed_microphone=page.get_by_role('dialog',name='Enable your meeting microphone')
                await resumed_microphone.get_by_role('button',name='Continue Without Microphone',exact=True).click()
                await expect(page.get_by_test_id('bfg-recording-state')).to_have_count(0)
                await page.get_by_test_id('private-facilitation-guide').wait_for()
            names=('Alex Morgan','Taylor Reed','Jordan Ellis')+('Sample Leader',)*6
            for index,name in enumerate(names):
                await expect(review.locator('.bfg-eyebrow').first).to_contain_text(name)
                if index==1:
                    await expect(participant_pages[0].locator('.bfg-eyebrow').first).to_contain_text('Taylor Reed')
                await review.get_by_role('button',name='Approve Audience' if index==0 else 'Disapprove Audience',exact=True).click()
                await expect(review.get_by_text('Decision: adopted' if index==0 else 'Decision: rejected',exact=True)).to_be_visible()
                await review.get_by_role('button',name='NEXT FUNDING AUDIENCE' if index<len(names)-1 else 'DISCUSS PARTICIPATION',exact=True).click()
            await review.get_by_role('combobox',name='Person agreeing to participate',exact=True).select_option(label='Alex Morgan')
            await review.get_by_role('textbox',name='Confirmed contribution',exact=True).fill('Introduce two interested employers.')
            await review.get_by_role('checkbox',name='This person has explicitly agreed to this contribution.',exact=True).check()
            await review.get_by_role('button',name='SAVE CONFIRMED PARTICIPATION',exact=True).click()
            await review.get_by_role('button',name='REVIEW THE AGREED STRATEGY',exact=True).click()
            transcript=page.get_by_test_id('transcript-contributions')
            await transcript.get_by_role('checkbox',name='I have reviewed the transcript and recorded the ideas and responsibilities the board agreed to adopt.',exact=True).check()
            await transcript.get_by_role('button',name='Confirm Transcript Review',exact=True).click()
            await transcript.get_by_text('Your review is saved.',exact=False).wait_for()
            await review.get_by_role('button',name='REVIEW THE AGREED STRATEGY',exact=True).click()
            await review.get_by_role('checkbox',name='I confirm that this is the direction agreed during our meeting.',exact=True).check()
            await review.get_by_role('button',name='ADOPT OUR AGREED DIRECTION',exact=True).click()
            for pp in participant_pages:
                await pp.get_by_role('checkbox',name='I acknowledge the agreed direction and the contribution I have personally accepted.',exact=True).check()
                await pp.get_by_role('button',name='Adopt This Strategy',exact=True).click()
                await pp.get_by_text('You have acknowledged this agreed direction.',exact=True).wait_for()
            await participant_pages[0].screenshot(path=f'test_reports/current-simplified-participant-{width}.png',full_page=True)
            await review.get_by_role('button',name='Close Meeting and Prepare Our Strategy',exact=True).click()
            await review.get_by_role('heading',name='Thank you for playing The Fundraising Game.',exact=True).wait_for()
            await participant_pages[0].get_by_text('Your organization has now agreed on its fundraising strategy.',exact=True).wait_for()
            results.append({'width':width,'case':'audience_order_private_guide_three_synced_devices_transcript_and_adoption','passed':True})
            await page.get_by_role('link',name='Return to My Workspace',exact=True).click()
            await page.get_by_role('button',name='Download Final Fundraising Strategy',exact=True).click()
            import io
            from PIL import Image
            logo=io.BytesIO();Image.new('RGB',(40,40),'navy').save(logo,format='PNG')
            await page.get_by_label('Organization logo',exact=True).set_input_files({'name':'organization-logo.png','mimeType':'image/png','buffer':logo.getvalue()})
            await expect(page.get_by_alt_text('Organization logo preview',exact=True)).to_be_visible()
            await page.get_by_label('Primary color',exact=True).fill('#123456')
            async with page.expect_download() as final_document:
                await page.get_by_role('button',name='Save Colors and Download PDF',exact=True).click()
            assert (await final_document.value).suggested_filename=='fundraising-strategy.pdf'
            await (await final_document.value).save_as(f'test_reports/current-simplified-strategy-{width}.pdf')
            await expect(page.get_by_role('button',name='Generate Board Portfolios',exact=True)).to_have_count(0)
            await page.evaluate('''()=>{const original=navigator.clipboard.writeText.bind(navigator.clipboard);let deny=true;navigator.clipboard.writeText=async text=>{if(deny){deny=false;throw new DOMException('Copy denied for this test','NotAllowedError')}return original(text)}}''')
            await page.get_by_role('button',name='Copy Strategy Email',exact=True).click()
            await expect(page.get_by_role('textbox',name='Strategy link or email',exact=True)).to_contain_text('/strategy/')
            await page.get_by_role('button',name='Copy Strategy Email',exact=True).click()
            await page.get_by_role('button',name='Strategy Email Copied',exact=True).wait_for()
            shared_url=await page.get_by_role('link',name='View Shared Strategy',exact=True).get_attribute('href')
            await participant_pages[0].goto(BASE+shared_url)
            await participant_pages[0].get_by_test_id('bfg-shared-strategy-page').wait_for()
            async with participant_pages[0].expect_download() as shared_document:
                await participant_pages[0].get_by_role('link',name='Download Adopted Strategy',exact=True).click()
            assert (await shared_document.value).suggested_filename=='fundraising-strategy.pdf'
            assert await page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2')
            await page.screenshot(path=f'test_reports/current-simplified-approved-{width}.png',full_page=True)
            results.append({'width':width,'case':'branded_adopted_strategy_and_secure_sharing_without_portfolios','passed':True})
            for pc in participant_contexts:await pc.close()
            await context.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
            await page.goto(BASE+'/admin?tab=home')
            await page.get_by_test_id('fundraising-admin').wait_for()
            await page.get_by_role('button',name='Homepage Editor',exact=True).click()
            await page.get_by_label('Page heading',exact=True).fill('Our board fundraising homepage')
            await page.get_by_role('button',name='Save Website Content',exact=True).click()
            await page.get_by_text('Your changes are saved and appear on the public website after refresh.',exact=True).wait_for()
            await page.goto(BASE)
            await page.get_by_role('heading',name='Our board fundraising homepage',exact=True).wait_for()
            await page.goto(BASE+'/admin?tab=how')
            await page.get_by_role('button',name='How It Works Editor',exact=True).click()
            await page.get_by_label('Page heading',exact=True).fill('Our guided board fundraising meeting')
            await page.get_by_role('button',name='Save Website Content',exact=True).click()
            await page.get_by_text('Your changes are saved and appear on the public website after refresh.',exact=True).wait_for()
            await page.goto(BASE+'/how-the-fundraising-game-works')
            await page.get_by_role('heading',name='Our guided board fundraising meeting',exact=True).wait_for()
            results.append({'width':width,'case':'both_admin_editors_save_independently_and_public_refresh','passed':True})
            await context.add_cookies([{'name':'member_access_token','value':member_token,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
            await page.goto(BASE+'/admin?tab=tests')
            await page.get_by_role('button',name='Start Fresh Fundraising Game Test',exact=True).click()
            await page.wait_for_url(BASE+'/')
            await page.get_by_role('heading',name='Our board fundraising homepage',exact=True).wait_for()
            assert not await page.evaluate("localStorage.getItem('fundraisingLeadToken')")
            new_token=await page.evaluate("localStorage.getItem('memberToken')")
            current=await context.request.get(BASE+'/api/members/me',headers={'Authorization':'Bearer '+new_token})
            assert current.ok,await current.text()
            assert (await current.json())['member']['user_id']!=test['member']['user_id']
            results.append({'width':width,'case':'fresh_admin_test_uses_new_identity_after_previous_member_session','passed':True})
            assert not errors,errors
            await context.close()
        await browser.close()
    Path('test_reports/current-simplified-browser.json').write_text(json.dumps({'passed':True,'cases':results},indent=2))
    print('PASS:',len(results),'simplified desktop/mobile browser checks')

if __name__=='__main__':Path('test_reports').mkdir(exist_ok=True);asyncio.run(main())
