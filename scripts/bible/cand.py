import json, re, unicodedata
FINAL=str.maketrans('ךםןףץ','כמנפצ')
def strip(s):
    s=''.join(ch for ch in unicodedata.normalize('NFD',s) if not unicodedata.combining(ch))
    s=re.sub(r'[־\-–]',' ',s); s=re.sub(r'\(.*?\)','',s)
    s=re.sub(r'[^א-ת ]','',s)
    return re.sub(r'\s+',' ',s).strip()
def skel(s):
    s=strip(s).translate(FINAL).replace(' ','')
    return (s[0]+re.sub('[ויא]','',s[1:])) if s else s
P=json.load(open('places.json'))
L=json.load(open('/home/claude/watcher/data/localities.json'))['locs']
exact={}; sk={}
for k,v in P.items():
    pl=v['plain']
    if not pl: continue
    for form in {pl, pl.replace(' ','')}:
        exact.setdefault(form.translate(FINAL),[]).append(k)
    sk.setdefault(skel(pl),[]).append(k)
STOP=set('מגדל צור גבעה גבעת רמה רמת עין כפר גן תל הר עמק קרית ראש מעלה נחל אבן באר חצר אלון נווה שדה בית עיר מצפה נאות נוף אור מבוא שער משמר מעגן אפיק גשר נצר עטרת כוכב שבות מושב קיבוץ גבעות חוות נאה טל ים מי נס זכרון אבני יד הוד בני בן גאולי שבי עזר אשל חורשת מרכז חדשה החדשה העליון התחתון עילית מערב מזרח שער'.split())
out=[]
for l in L:
    name=strip(l['he']); 
    if not name: continue
    toks=name.split()
    hits=[]
    full=name.translate(FINAL)
    for form in (full, full.replace(' ','')):
        if form in exact: hits.append(('full',exact[form]))
    if not hits and skel(name) in sk and len(skel(name))>=3: hits.append(('full-skel',sk[skel(name)]))
    if not hits:
        n=len(toks)
        for size in range(n-1,0,-1):
            for i in range(0,n-size+1):
                g=' '.join(toks[i:i+size]).translate(FINAL)
                if size==1 and (toks[i] in STOP or len(toks[i])<3): continue
                if g in exact: hits.append((f'part:{g}',exact[g]))
                elif size==1 and len(skel(g))>=4 and skel(g) in sk: hits.append((f'partskel:{g}',sk[skel(g)]))
            if hits: break
    if hits: out.append({'c':l['c'],'he':l['he'],'en':l['en'],'r':l['r'],'hits':[(h[0],[(k,P[k]['kjv']) for k in h[1]]) for h in hits]})
json.dump(out,open('cands.json','w'),ensure_ascii=False,indent=0)
print(len(out),'of',len(L))
from collections import Counter
print(Counter(o['hits'][0][0].split(':')[0] for o in out))
