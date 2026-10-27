import re, json, unicodedata, xml.etree.ElementTree as ET
NS={'o':'http://www.bibletechnologies.net/2003/OSIS/namespace'}
src=open('/home/claude/bible/strongs/hebrew/StrongHebrewG.xml',encoding='utf-8').read()
FINAL=str.maketrans('ךםןףץ','כמנפצ')
def strip(s):
    s=''.join(ch for ch in unicodedata.normalize('NFD',s) if not unicodedata.combining(ch))
    s=s.replace('־',' ').replace('־',' ')
    s=re.sub(r'[^א-ת ]','',s)
    return re.sub(r'\s+',' ',s).strip()
def skel(s):
    s=strip(s).translate(FINAL).replace(' ','')
    return s[0]+re.sub('[וי]','',s[1:]) if s else s
entries={}
for m in re.finditer(r'<div type="entry" n="(\d+)">(.*?)</div>\s*(?=<div type="entry"|</div>)',src,re.S):
    n,body=m.groups()
    w=re.search(r'<w ([^>]*)>([^<]*)</w>',body)
    if not w: continue
    attrs=dict(re.findall(r'(\w+)="([^"]*)"',w.group(1)))
    mo=attrs.get('morph','')
    if 'loc' not in mo and not (mo=='n-pr'): continue
    tr=re.search(r'<note type="translation">(.*?)</note>',body,re.S)
    ex=re.search(r'<note type="explanation">(.*?)</note>',body,re.S)
    items=re.findall(r'<item>(.*?)</item>',body,re.S)
    clean=lambda x: re.sub(r'<[^>]+>','',x or '').strip()
    entries['H'+n]={'lemma':attrs.get('lemma',''),'plain':strip(attrs.get('lemma','')),'xlit':attrs.get('xlit',''),
        'kjv':clean(tr.group(1)) if tr else '','expl':clean(ex.group(1)) if ex else '','items':[clean(i) for i in items]}
ent2={}
for k,v in entries.items():
    blob=(v['expl']+' '+' '.join(v['items'])).lower()
    if re.search(r'place|city|town|region|country|land|mount|river|valley|well|brook|wilderness|district|stream|plain|hill|sea|village',blob): ent2[k]=v
entries=ent2
print('places',len(entries))
json.dump(entries,open('/home/claude/bible/work/places.json','w'),ensure_ascii=False,indent=0)
