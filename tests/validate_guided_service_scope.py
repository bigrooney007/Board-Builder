"""Guided-service changes preserve the Fundraising Game and legacy product infrastructure."""
import ast,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='0eb3f603534d3ceba14c66b12ea5ca1a2bd5a659'
def original(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT,text=True)
protected=['backend/fundraising_launch.py','backend/fundraising_launch_content.json','backend/fundraising_audiences.py','backend/game_routes.py','backend/game_night_routes.py','backend/group_game_routes.py','backend/game_meeting_routes.py','backend/strategy_routes.py','backend/strategic_questionnaire.py','backend/guided_product_routes.py','backend/marketing_routes.py','backend/blog_service.py','backend/blog_feed.py','backend/ai_service.py','frontend/src/funnels/RecruitFreePage.jsx','frontend/src/funnels/RecruitQuestionsPage.jsx','frontend/src/member/RecruitCampaignSetupPage.jsx','frontend/src/member/RecruitCampaignMaterialsPage.jsx','frontend/src/game/FundraisingSetup.jsx','frontend/src/game/FundraisingWorkspace.jsx','frontend/src/game/GroupGamePage.jsx','frontend/src/game/GroupPlayPage.jsx','frontend/src/game/StrategyPage.jsx','frontend/src/game/AudienceQuestionnaire.jsx','frontend/src/admin/FacilitatorWorkspace.jsx','frontend/src/content/testimonials.js','frontend/src/pages/MainHomePage.jsx','frontend/src/pages/MainHomePage.css','frontend/yarn.lock']
for p in protected:assert (ROOT/p).read_text()==original(p),p+' changed outside scope'
def line_items(s):return [ast.dump(v,include_attributes=False) for n in ast.walk(ast.parse(s)) if isinstance(n,ast.Dict) for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant) and k.value=='line_items']
assert line_items((ROOT/'backend/payment_routes.py').read_text())==line_items(original('backend/payment_routes.py')),'An existing product checkout changed'
paths=lambda s:set(re.findall(r'<Route\s+path=([^>]+?)\s+element=',s))
assert paths(original('frontend/src/App.js'))<=paths((ROOT/'frontend/src/App.js').read_text()),'An existing route was removed'
print('PASS guided service scope: Fundraising Game, original Planning questions, legacy routes, AI engines, homepage, testimonials and blog infrastructure preserved')
