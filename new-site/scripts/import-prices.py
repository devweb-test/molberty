"""Import the text layer of the supplied three-page PDF using Ghostscript."""
from pathlib import Path
import subprocess,re,json,tempfile,shutil
root=Path(__file__).resolve().parents[1]
source=root.parent/'Praiss_total_2026.pdf'
if not source.exists():source=root/'assets/documents/price-list-2026.pdf'
assert source.is_file(), 'Missing supplied 2026 price PDF'
with tempfile.TemporaryDirectory() as temp:
 text_path=Path(temp)/'prices.txt'
 result=subprocess.run(['gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=txtwrite','-sOutputFile='+str(text_path),str(source)],capture_output=True,text=True)
 if result.returncode:raise RuntimeError(result.stderr)
 text=text_path.read_text()
groups=[('artists','Мольберты для художников'),('studio','Оборудование для изостудий'),('palettes','Палитры из фанеры'),('boards','Планшеты и клипборды'),('exhibition','Мольберты для выставок'),('interior','Мольберты для интерьера'),('souvenirs','Мольберты-сувениры')]
sections=[{'id':id,'name':name,'items':[]} for id,name in groups];current=0
for line in text.splitlines():
 if '@' in line:continue
 if 'Оборудование для изостудий.' in line:current=1;continue
 if 'ПАЛИТРЫ (фанера)' in line:current=2;continue
 if 'ПЛАНШЕТЫ (фанера)' in line:current=3;continue
 if 'Мольберты для выставок.' in line:current=4;continue
 if 'Мольберты для интерьера.' in line:current=5;continue
 if 'Мольберты-сувениры.' in line:current=6;continue
 match=re.search(r'(?<!\d)(\d+)\.\s{2,}(.+)',line)
 if not match:continue
 number=int(match.group(1));tail=match.group(2).strip()
 values=list(re.finditer(r'(?:от\s+)?\d+-\d{2}|(?<!\S)-(?!\S)',tail))
 name=tail[:values[0].start()].strip() if values else tail
 if current==6:name=re.split(r'\s{2,}',name)[-1]
 name=re.sub(r'\s+',' ',name).replace('“','«')
 prices=[{'value':None,'from':False} if v.group()=='-' else {'value':int(re.search(r'\d+',v.group()).group()),'from':v.group().startswith('от')} for v in values]
 wholesale,retail=None,None
 if current==5:
  assert len(prices)==1,(number,tail);retail=prices[0]
 elif current==6:
  assert len(prices)==1,(number,tail);wholesale=prices[0]
 elif prices:
  assert len(prices)==2,(number,tail);wholesale,retail=prices
 else:assert current==0 and number==12,(current,number,tail)
 item={'id':sections[current]['id']+'-'+str(number),'number':number,'name':name,'wholesale':wholesale['value'] if wholesale else None,'retail':retail['value'] if retail else None,'wholesaleFrom':wholesale['from'] if wholesale else False,'retailFrom':retail['from'] if retail else False}
 if current==6:item['type']='Мольберты-треноги (бук)' if number<=5 else 'Мольберты «Лира» (бук)'
 if current==0:
  item['type']=next(label for low,high,label in [(1,6,'Станковые'),(7,12,'Трансформеры'),(13,22,'Лира'),(23,25,'А-стиль'),(26,32,'Хлопушки'),(33,34,'Столы для рисования'),(35,41,'Настольные'),(42,43,'Настольные планшеты')] if low<=number<=high)
 if wholesale is None and retail is None:item['note']='В исходном прайсе цена не указана.'
 sections[current]['items'].append(item)
assert [len(s['items']) for s in sections]==[43,29,4,9,8,6,7]
assert [x['number'] for x in sections[0]['items']]==list(range(1,44))
assert [x['number'] for x in sections[1]['items']]==list(range(44,73))
assert sections[0]['items'][11]['retail'] is None
assert sections[5]['items'][4]['retailFrom'] is True
assert sections[1]['items'][22]['retail']==11500
output={'title':'Прайс-лист Мольберты.RU','effectiveDate':'2026-01-01','currency':'RUB','sourceFile':'assets/documents/price-list-2026.pdf','count':sum(len(s['items']) for s in sections),'sections':sections}
(root/'data/prices.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
destination=root/'assets/documents/price-list-2026.pdf'
if source.resolve()!=destination.resolve():shutil.copy2(source,destination)
print(f'Imported {output["count"]} positions in {len(sections)} sections; blank prices preserved.')
