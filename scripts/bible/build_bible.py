import json, re, math, sys
sys.path.insert(0, '/home/claude/bible/work')
from curate import NAMED, SITES
B = {b['name']: b['chapters'] for b in json.load(open('/home/claude/bible/kjv.json', encoding='utf-8-sig'))}
def verse(book, c, v):
    t = B[book][c - 1][v - 1]
    return re.sub(r'\s+', ' ', t.replace('{', '').replace('}', '')).strip()
def fragment(text, kw, limit=150):
    i = text.lower().find(kw.lower())
    if i < 0: return None
    # clause boundaries around the keyword
    starts = [m.end() for m in re.finditer(r'[;:.?!]\s', text[:i])]
    s = starts[-1] if starts else 0
    m = re.search(r'[;:.?!](\s|$)', text[i + len(kw):])
    e = i + len(kw) + (m.start() + 1 if m else len(text) - i - len(kw))
    frag = text[s:e].strip()
    if len(frag) < 40 and e < len(text):  # too short: take the next clause too
        m2 = re.search(r'[;:.?!](\s|$)', text[e:])
        e = e + (m2.start() + 1 if m2 else len(text) - e)
        frag = text[s:e].strip()
    if len(frag) > limit:
        a = max(0, i - s - 60)
        piece = frag[a:a + limit]
        if a > 0 and ' ' in piece: piece = piece[piece.index(' ') + 1:]
        if a + limit < len(frag) and ' ' in piece: piece = piece[:piece.rindex(' ')]
        frag = ('…' if a > 0 else '') + piece.strip().rstrip(',;:') + ('…' if a + limit < len(frag) else '')
        if s > 0 and not frag.startswith('…'): frag = '…' + frag
    else:
        if s > 0: frag = '…' + frag
        if e < len(text) and not frag.endswith(('.', '!', '?')): frag = frag.rstrip(',;:') + '…'
    frag = frag.replace('.…', '.').replace(':…', '…')
    if frag[-1] in ',;:': frag = frag[:-1] + '…'
    frag = frag[0].upper() + frag[1:] if frag[0] != '…' else frag
    return frag
bad = []
def ref(book, c, v): return f'{book} {c}:{v}'
L = json.load(open('/home/claude/watcher/data/localities.json'))['locs']
out = {}
for code, (name, book, c, v, kw, note) in NAMED.items():
    t = verse(book, c, v); f = fragment(t, kw)
    if not f: bad.append((code, name, ref(book, c, v), kw, t)); continue
    out[str(code)] = {'k': 'name', 'n': name, 'r': ref(book, c, v), 'q': f, **({'x': note} if note else {})}
sites = []
for (name, lat, lon, book, c, v, kw) in SITES:
    t = verse(book, c, v); f = fragment(t, kw)
    if not f: bad.append(('site', name, ref(book, c, v), kw, t)); continue
    sites.append((name, lat, lon, ref(book, c, v), f))
def km(a, b, c, d):
    R = 6371; p = math.radians
    x = math.sin(p(c - a) / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))
codes = {l['c'] for l in L}
missing = [c for c in NAMED if c not in codes]
for l in L:
    if str(l['c']) in out or l['lat'] is None: continue
    best = min(sites, key=lambda s: km(l['lat'], l['lon'], s[1], s[2]))
    d = km(l['lat'], l['lon'], best[1], best[2])
    out[str(l['c'])] = {'k': 'near', 'n': best[0], 'd': max(1, round(d)), 'r': best[3], 'q': best[4]}
json.dump({'note': 'Verses: King James Version (public domain). Biblical place names matched against Strong\'s Hebrew lexicon.', 'b': out},
          open('/home/claude/watcher/data/bible.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('named', sum(1 for v in out.values() if v['k'] == 'name'), 'near', sum(1 for v in out.values() if v['k'] == 'near'), 'total', len(out), 'of', len(L))
print('codes not in locality list:', missing)
for b in bad: print('NO KEYWORD:', b)
