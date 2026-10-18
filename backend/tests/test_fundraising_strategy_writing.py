import copy
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fundraising_strategy_writing import written_strategy,document_sections
from strategy_pdf import build_strategy_pdf

def approved():
    return {"revision":"approved-source","commitments":[],"audiences":[{"id":"teachers","category":"individuals","contributor":"Alex Morgan","strategy":{
        "audience_name":"Teachers in Pittsburgh","who_why":"Alex Morgan said teachers in Pittsburgh benefit from the children we help.",
        "where":"Teachers congregate in local professional communities. We can join these communities.",
        "attraction":"We will offer a free teaching-career guide in exchange for their name and email address.",
        "process":"We will send follow-up emails about our work and invite teachers to an event before asking for support.",
        "ask":"We will ask teachers to fund a backpack for a student.","amount":"We will ask for $100 for each backpack.",
        "follow_up":"We will respectfully invite teachers who have not given to our next event.",
        "stewardship":"We will send a thank-you email and ask an agreed board member to call each donor."}}]}

class Writing(unittest.IsolatedAsyncioTestCase):
    async def test_source_only_editorial_output_and_optional_details(self):
        agreed=approved();before=copy.deepcopy(agreed)
        edited={"audiences":[{"id":"teachers","why":{"text":"Teachers would give because they benefit from the children we help.","quote":"teachers in Pittsburgh benefit from the children we help."},
            "amount":{"text":"We will ask for $9999 for each backpack.","quote":"We will ask for $100 for each backpack."},
            "where":{"text":"We will buy a national list.","quote":"An invented source quote"}}]}
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(return_value=edited)):
            result=await written_strategy(agreed)
        row=result['audiences'][0]
        self.assertIn('Teachers would give because',row['why'])
        self.assertNotIn('Alex Morgan said',str(row));self.assertIn('$100',row['amount']);self.assertNotIn('$9999',str(row))
        self.assertNotIn('national list',str(row));self.assertEqual(agreed,before)
        self.assertTrue(row['follow_up']);self.assertTrue(row['stewardship'])
    async def test_provider_failure_keeps_finished_source_without_attribution_or_invented_stewardship(self):
        value=approved();value['audiences'][0]['strategy'].pop('follow_up');value['audiences'][0]['strategy'].pop('stewardship')
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(side_effect=RuntimeError('provider unavailable'))):
            result=await written_strategy(value)
        row=result['audiences'][0];self.assertNotIn('Alex Morgan said',str(row));self.assertFalse(row['stewardship']);self.assertFalse(row['follow_up'])
        value['written_audiences']=result['audiences'];sections=document_sections(value,{'goal':{'amount':100000}})
        self.assertNotIn('Steward',str(sections));self.assertNotIn('Alex Morgan said',str(sections))
    async def test_each_audience_starts_its_own_pdf_page_with_bold_subheadings(self):
        from pypdf import PdfReader
        value=approved();second=copy.deepcopy(value['audiences'][0]);second['id']='businesses';second['category']='businesses';second['strategy']['audience_name']='Local Architecture Businesses';second['strategy']['who_why']='Local architecture businesses support youth education.';value['audiences'].append(second)
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(side_effect=RuntimeError('provider unavailable'))):result=await written_strategy(value)
        value['written_audiences']=result['audiences'];sections=document_sections(value,{'goal':{'amount':100000},'organization':{'mission':'Help children.'}})
        pdf=build_strategy_pdf({'schema_version':7,'document_sections':sections,'document_text':'unused raw text','branding':{'primary_color':'#123456'}},'Example Organization')
        pages=[p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages]
        teachers=next(i for i,p in enumerate(pages) if '1. Teachers in Pittsburgh' in p)
        businesses=next(i for i,p in enumerate(pages) if '2. Local Architecture Businesses' in p)
        self.assertNotEqual(teachers,businesses);self.assertNotIn('2. Local Architecture Businesses',pages[teachers])
        self.assertIn('Why They Would Give',pages[teachers]);self.assertIn('How Much We Will Ask For',pages[teachers]);self.assertIn('$100',pages[teachers])
        self.assertNotIn('Alex Morgan said','\n'.join(pages));self.assertNotIn('unused raw text','\n'.join(pages))
        self.assertIn(b'/Helvetica-Bold',pdf)

if __name__=='__main__':unittest.main()
