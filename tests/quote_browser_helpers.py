"""Exercise the current post-payment form rather than bypassing its new gate."""
from playwright.async_api import expect
BASE='http://127.0.0.1:8765'

async def complete_leader(page,service,token,width=None,audience_player=None):
 await page.get_by_test_id('paid-leader-questionnaire').wait_for()
 data=await (await page.request.get(BASE+f'/api/services/{service}/customer/{token}/leader-questions')).json()
 if data.get('completed'):return
 await page.get_by_test_id('paid-leader-questionnaire').wait_for()
 if width:await page.screenshot(path=f'test_reports/current-flow-{service}-paid-leader-{width}.png',full_page=True)
 if not data.get('details_completed'):
  for i,q in enumerate(data['questions']):
   value=data.get('answers',{}).get(q['id']) or ('3' if q['key'] in ('board_count','board_size','desired_count') else '100000' if q['type']=='number' else '2027-12-31' if q['type']=='date' else 'Help children access learning through agreed programs and partnerships.')
   if q['type']=='multiselect':await page.get_by_role('checkbox',name=q['options'][0],exact=True).check()
   elif q['type']=='select':await page.get_by_role('combobox').select_option(q['options'][0])
   else:await page.get_by_label('Your answer',exact=True).fill(str(value))
   await page.get_by_role('button',name=data['copy']['leader_submit'] if i==len(data['questions'])-1 else 'SAVE AND CONTINUE',exact=True).click()
   if i<len(data['questions'])-1:await expect(page.get_by_text(f'Question {i+2} of {len(data["questions"])}',exact=True)).to_be_visible()
 if service=='board-fundraising':
  if audience_player:await audience_player(page,True)
  else:
   await page.get_by_role('button',name='START MY GAME',exact=True).click()
   for _ in range(3):await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
   await page.get_by_role('textbox',name='Your personal participation',exact=True).fill('I will discuss practical contributions with our board.')
   await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click();await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
 await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).wait_for()
