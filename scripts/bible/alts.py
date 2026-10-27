import sys; sys.path.insert(0,'.')
from listy import occurrences, listiness
kws = sys.argv[1].split('|')
for kw in kws:
    occ = occurrences(kw)
    occ = sorted(occ, key=lambda o: listiness(o[3]))
    print(f'## {kw} ({len(occ)})')
    for b,c,v,t in occ[:5]:
        print(f'  {listiness(t):.2f} {b} {c}:{v} | {t[:170]}')
