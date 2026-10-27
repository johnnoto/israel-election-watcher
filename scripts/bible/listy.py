import json, re, sys
sys.path.insert(0,'.')
from curate import NAMED, SITES
B = {b['name']: b['chapters'] for b in json.load(open('/home/claude/bible/kjv.json', encoding='utf-8-sig'))}
OT = list(B)[:39]
def verse(book,c,v): return re.sub(r'\s+',' ',B[book][c-1][v-1].replace('{','').replace('}',''))
def listiness(t):
    caps = re.findall(r'\b[A-Z][a-z]+(?:-[a-z]+)*\b', t)
    words = len(t.split())
    ands = len(re.findall(r'\band\b', t))
    commas = t.count(',')
    names = sum(1 for w in caps if w not in ('And','The','Then','So','But','For','LORD','God','I','He','They','Now','Behold','O','Wherefore','Neither'))
    return round((names*2 + commas) / max(words,1), 2)
def occurrences(kw):
    out=[]
    for b in OT:
        for ci,ch in enumerate(B[b]):
            for vi,t in enumerate(ch):
                tt=t.replace('{','').replace('}','')
                if re.search(r'(?<![A-Za-z-])'+re.escape(kw)+r'(?![A-Za-z])', tt): out.append((b,ci+1,vi+1,re.sub(r'\s+',' ',tt)))
    return out
def _report():
    rows=[]
    seen=set()
    for code,(name,b,c,v,kw,note) in NAMED.items():
        key=(name,b,c,v)
        if key in seen: continue
        seen.add(key)
        t=verse(b,c,v); s=listiness(t)
        occ=occurrences(kw)
        rows.append((s,code,name,f'{b} {c}:{v}',kw,len(occ),t[:110]))
    rows.sort(reverse=True)
    for r in rows: print(r[0], r[1], r[2], '|', r[3], '| kw', r[4], '| occ', r[5], '|', r[6])
if __name__=="__main__": _report()
