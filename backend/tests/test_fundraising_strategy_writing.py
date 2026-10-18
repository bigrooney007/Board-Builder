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
    async def test_detailed_approved_followup_stewardship_and_offer_are_not_shortened(self):
        value=approved();source=value['audiences'][0]['strategy']
        source['where']='We can find teachers in Facebook and LinkedIn groups, join teachers communities and run targeted ads.'
        source['ask']='We will ask for a backpack for a student. For every backpack funded, 10 teachers receive our free guide.'
        source['follow_up']='We will follow up by email, call and invite them to the next teachers event. Unless they unsubscribe, they will remain part of our quarterly fundraising campaign.'
        source['stewardship']='We will immediately send a thank-you email, send a Christmas card annually, arrange a personal call from an agreed board member and invite donors to support the next backpack programme.'
        output={'audiences':[{'id':'teachers','title':{'text':'A Different City','quote':source['who_why']},'where':{'text':'We will reach teachers online.','quote':source['where']},'ask':{'text':'We will ask for a backpack for a student.','quote':source['ask']},'follow_up':{'text':'We will follow up by email.','quote':source['follow_up']},'stewardship':{'text':'We will send a thank-you email.','quote':source['stewardship']}}]}
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(return_value=output)):result=await written_strategy(value)
        row=result['audiences'][0]
        for detail in ('Facebook','LinkedIn','10 teachers','unsubscribe','quarterly','Christmas','annually','personal call'):
            self.assertIn(detail,str(row))
        self.assertEqual(row['title'],'Teachers in Pittsburgh')
        value['written_audiences']=result['audiences'];section=document_sections(value,{})[1]
        self.assertEqual(section['eyebrow'],'Ideal Funding Audience:')
        self.assertEqual(len([b for b in section['blocks'] if b['kind']=='bullet_heading']),8)

    async def test_next_audience_does_not_inherit_the_teachers_strategy(self):
        value=approved();value['audiences'].append({'id':'parents','category':'individuals','contributor':'Taylor Reed','strategy':{'audience_name':'Parents in Pittsburgh (Ages 5 to 12)','who_why':'Parents in Pittsburgh (Ages 5 to 12)'}})
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(side_effect=RuntimeError('provider unavailable'))):result=await written_strategy(value)
        parent=result['audiences'][1]
        self.assertEqual(parent['title'],'Parents in Pittsburgh (Ages 5 to 12)')
        self.assertFalse(parent['ask']);self.assertFalse(parent['amount']);self.assertFalse(parent['follow_up']);self.assertFalse(parent['stewardship'])
        self.assertNotIn('backpack',str(parent));self.assertNotIn('teachers',str(parent).lower())

    async def test_source_only_editorial_output_and_optional_details(self):
        agreed=approved();before=copy.deepcopy(agreed)
        edited={"audiences":[{"id":"teachers","why":{"text":"Teachers in Pittsburgh would give because they benefit from the children we help.","quote":"teachers in Pittsburgh benefit from the children we help."},
            "amount":{"text":"We will ask for $9999 for each backpack.","quote":"We will ask for $100 for each backpack."},
            "where":{"text":"We will buy a national list.","quote":"An invented source quote"}}]}
        with patch('fundraising_strategy_writing.edit_approved_audiences',new=AsyncMock(return_value=edited)):
            result=await written_strategy(agreed)
        row=result['audiences'][0]
        self.assertIn('Teachers in Pittsburgh would give because',row['why'])
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
    async def test_full_eight_part_audience_fits_one_legible_page(self):
        from pypdf import PdfReader
        section = {'key': 'audience_1',
         'title': '1. Teachers in Pittsburgh',
         'eyebrow': 'Ideal Funding Audience:',
         'blocks': [{'kind': 'bullet_heading', 'text': 'Why They Would Give'},
                    {'kind': 'body',
                     'text': 'They benefit from what we do. When a child is empowered, the teacher has an easier job '
                             'to do.'},
                    {'kind': 'bullet_heading', 'text': 'Where We Can Find Them'},
                    {'kind': 'body',
                     'text': 'They congregate in online communities such as Facebook and LinkedIn groups and discuss '
                             'education and child education online. We can find them by joining teachers communities '
                             'and running ads targeting them.'},
                    {'kind': 'bullet_heading', 'text': 'How We Will Attract Their Interest'},
                    {'kind': 'body',
                     'text': 'We can attract teachers by giving them a free resource, such as a guide to becoming '
                             'the best teacher they can be in five years. They can provide their names, email '
                             'addresses and where they work to receive it.'},
                    {'kind': 'bullet_heading', 'text': 'How We Will Raise Money From Them'},
                    {'kind': 'body',
                     'text': 'Once teachers receive our resource, we will send follow-up emails that help them know '
                             'and like our organization. We will introduce our organization, explain the good work '
                             'we do and share testimonials. To build trust, we can organize an event for teachers, '
                             'introduce them to the children we are helping and invite them to partner with us by '
                             'making a pledge.'},
                    {'kind': 'bullet_heading', 'text': 'What We Will Ask Them to Support'},
                    {'kind': 'body',
                     'text': 'We can ask them to support each child with a backpack for the next school session. For '
                             'every backpack they buy, 10 teachers across Pittsburgh receive our free guide to help '
                             'them get the best from their teaching careers.'},
                    {'kind': 'bullet_heading', 'text': 'How Much We Will Ask For'},
                    {'kind': 'body',
                     'text': 'Each backpack costs $100, plus logistics and administration fees. We will ask for $100 '
                             'for a backpack for a student.'},
                    {'kind': 'bullet_heading', 'text': 'How We Will Follow Up If They Do Not Give'},
                    {'kind': 'body',
                     'text': 'We will follow up through email, call them and invite them to our next teachers event. '
                             'This allows us to respectfully invite them to give again. Even when they do not give, '
                             'as long as they do not unsubscribe, they will remain part of our quarterly fundraising '
                             'campaign.'},
                    {'kind': 'bullet_heading', 'text': 'How We Will Thank and Steward Those Who Give'},
                    {'kind': 'body',
                     'text': 'We will send a thank-you email immediately, send a Christmas card annually, ask an '
                             'agreed board member to call and thank each donor personally, and invite them to '
                             'support the next backpack programme.'}]}
        pdf=build_strategy_pdf({'schema_version':7,'document_sections':[section],'branding':{'primary_color':'#233a72'}},'')
        pages=PdfReader(io.BytesIO(pdf)).pages
        self.assertEqual(len(pages),2)  # Cover, then the full audience.
        text=pages[1].extract_text()
        for detail in ('Facebook','LinkedIn','10 teachers','quarterly','unsubscribe','Christmas','personally'):
            self.assertIn(detail,text)
        sizes=[]
        pages[1].extract_text(visitor_text=lambda text,cm,tm,font,size:sizes.append(size) if 'They benefit from what we do' in text else None)
        self.assertTrue(sizes);self.assertTrue(all(size>=11 for size in sizes))

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
