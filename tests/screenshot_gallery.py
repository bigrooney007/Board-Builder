"""Portable screenshots gallery and compact review sheets from browser evidence."""
import base64,html,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path('test_reports');root.mkdir(exist_ok=True)
images=sorted(p for p in root.glob('current*.png') if 'failure' not in p.name)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
items=[]
for path in images:
 label=path.stem.removeprefix('current-').replace('-',' ')
 items.append(f'<article><h2>{html.escape(label)}</h2><a href="{html.escape(path.name)}"><img loading="lazy" src="{html.escape(path.name)}" alt="{html.escape(label)}"></a><p><a download href="{html.escape(path.name)}">Download full screenshot</a></p></article>')
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nonprofit Board Builder Screenshots</title><style>body{font:17px/1.6 Arial;background:#f4f5fc;color:#000;max-width:1440px;margin:auto;padding:28px}header{text-align:center}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}article{background:white;padding:16px;border:1px solid #ddd;border-radius:14px;overflow:hidden}h2{font-size:18px;text-transform:capitalize}img{width:100%;max-height:600px;object-fit:contain;object-position:top}a{color:#3730a3}</style><header><h1>Nonprofit Board Builder: Customer Flows and Workstations</h1><p>Actual browser captures using synthetic organizations and controlled providers. These screenshots show this GitHub build; they do not establish production deployment or live inbox delivery.</p></header><main>'''+''.join(items)+'</main>'
(root/'current-screenshots.html').write_text(page)
(root/'current-screenshot-index.json').write_text(json.dumps([p.name for p in images],indent=2))
# Compact contact sheets are included in the job log so the reviewing assistant
# can retrieve and inspect actual browser pixels without a production session.
for group in ('recruitment','recommitment','fundraising','planning','professional','workstations','admin'):
 if group=='admin':selected=[p for p in images if p.name.startswith('current-admin-') and '-1440' in p.name]
 elif group=='professional':selected=[p for p in images if any(x in p.name for x in ('meet-rooney','consultation','part-one-paid'))]
 elif group=='workstations':selected=[p for p in images if 'workstation' in p.name and '-1440' in p.name]
 else:selected=[p for p in images if group in p.name and ('flow-' in p.name or 'workstation-' in p.name) and '-1440' in p.name]
 selected=selected[:12]
 if not selected:continue
 columns=3;width=990;tile_w=330;tile_h=400;sheet=Image.new('RGB',(width,((len(selected)+columns-1)//columns)*tile_h),'#ffffff');draw=ImageDraw.Draw(sheet)
 for index,path in enumerate(selected):
  x=(index%columns)*tile_w;y=(index//columns)*tile_h
  label=path.stem.removeprefix('current-').replace('-',' ')
  words=label.split();lines=[];line=''
  for word in words:
   if len(line+' '+word)>34:lines.append(line);line=word
   else:line=(line+' '+word).strip()
  lines.append(line)
  draw.multiline_text((x+12,y+8),'\n'.join(lines[:3]),font=font,fill='#000000',spacing=3)
  im=Image.open(path).convert('RGB');im.thumbnail((tile_w-24,320));sheet.paste(im,(x+(tile_w-im.width)//2,y+70))
 target=root/f'current-review-{group}.jpg';sheet.save(target,quality=72,optimize=True)
 print('NBB_SCREENSHOT|'+target.name+'|'+base64.b64encode(target.read_bytes()).decode())
print('SCREENSHOT_GALLERY_COUNT',len(images))
