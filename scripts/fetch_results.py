#!/usr/bin/env python3
"""Fetch the Central Elections Committee's results files and write the watcher's data files.

Usage:
  python scripts/fetch_results.py                 # download live files from the CEC
  python scripts/fetch_results.py --local DIR     # read expc.csv and expb.csv from DIR (for tests)

Writes data/live.json (national + locality results) and data/boxes.json (ballot-box results).
Exits 0 and prints CHANGED or UNCHANGED, so the workflow knows whether to redeploy.
"""
import argparse, csv, hashlib, io, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8'))
SITE = CFG.get('results_site', 'https://votes26.bechirot.gov.il/').rstrip('/') + '/'
MEDIA = SITE.replace('votes', 'media', 1) + 'files/'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; GlobeInBriefElectionWatcher/1.0; +https://github.com)', 'Accept-Language': 'he,en;q=0.8'}
META_COLS = {'סמל ועדה', 'ברזל', 'שם ישוב', 'סמל ישוב', 'קלפי', 'ריכוז', 'שופט', 'בזב', 'מצביעים', 'פסולים', 'כשרים', 'חיצוניות', 'קלפי אחרת', ''}


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url + ('&' if '?' in url else '?') + f'_={int(time.time())}', headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:  # network hiccups are common on election night
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f'Could not download {url}: {last}')


def parse(raw):
    text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip() for h in rows[0]]
    parties = [h for h in head if h not in META_COLS]
    out = []
    for r in rows[1:]:
        d = dict(zip(head, r))
        try:
            int(str(d.get('סמל ישוב', '')).strip())
        except ValueError:
            continue
        out.append(d)
    return head, parties, out


def num(x):
    try:
        return int(float(str(x).strip() or 0))
    except ValueError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--local', help='read expc.csv/expb.csv from this folder instead of downloading')
    ap.add_argument('--out', default=os.path.join(ROOT, 'data'))
    a = ap.parse_args()

    tracked = [p['code'] for p in CFG['parties']]
    polls_close = datetime.strptime(CFG['polls_close_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    before_close = datetime.now(timezone.utc) < polls_close
    codes = tracked + ['OTHER']
    cec_time, test_env = None, False
    if a.local:
        expc = open(os.path.join(a.local, 'expc.csv'), 'rb').read()
        expb = open(os.path.join(a.local, 'expb.csv'), 'rb').read()
        test_env = os.path.exists(os.path.join(a.local, 'TEST'))
    else:
        try:
            html = get(SITE).decode('utf-8', 'replace')
            test_env = 'סביבת בדיקות' in html
            m = re.search(r'תוצאות נכון ל-\s*([0-9/]+\s+[0-9:]+)', html)
            cec_time = m.group(1) if m else None
        except Exception as e:
            print('warning: results page not reachable:', e, file=sys.stderr)
        expc = get(MEDIA + 'expc.csv')
        expb = get(MEDIA + 'expb.csv')

    def vec(d, parties):
        v = [0] * len(codes)
        for p in parties:
            n = num(d.get(p))
            if not n:
                continue
            v[codes.index(p) if p in tracked else len(codes) - 1] += n
        return v

    _, pc, crow = parse(expc)
    _, pb, brow = parse(expb)
    nb = {}
    boxes = {}
    for d in brow:
        c = num(d['סמל ישוב'])
        if num(d.get('מצביעים')) == 0 and num(d.get('כשרים')) == 0:
            continue  # box listed but not counted yet
        nb[c] = nb.get(c, 0) + 1
        boxes.setdefault(str(c), []).append([d.get('קלפי', '').strip(), num(d.get('בזב')), num(d.get('מצביעים')), num(d.get('פסולים')), vec(d, pb)])
    locs, nat = [], {'r': 0, 't': 0, 'x': 0, 'v': [0] * len(codes), 'boxes': 0}
    for d in crow:
        c = num(d['סמל ישוב'])
        v = vec(d, pc)
        r, t, x = num(d.get('בזב')), num(d.get('מצביעים')), num(d.get('פסולים'))
        if t == 0 and sum(v) == 0:
            continue
        locs.append([c, d.get('שם ישוב', '').strip(), r, t, x, nb.get(c, 0), v])
        nat['r'] += r; nat['t'] += t; nat['x'] += x
        nat['v'] = [p + q for p, q in zip(nat['v'], v)]
    nat['boxes'] = sum(nb.values())
    unknown = sorted(set(pc) - set(tracked))
    if not a.local:
        # Anything published before polls close is test data, whatever the page says.
        if before_close:
            test_env = True
        if CFG.get('force_live'):
            test_env = False
    body = {'codes': codes, 'national': nat, 'locs': locs}
    digest = hashlib.sha1(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    live_path = os.path.join(a.out, 'live.json')
    prev = json.load(open(live_path, encoding='utf-8')) if os.path.exists(live_path) else {}
    changed = prev.get('digest') != digest or prev.get('test_env') != test_env
    live = {'status': 'counting' if locs else 'pre', 'test_env': test_env, 'cec_time': cec_time,
            'fetched_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'digest': digest,
            'other_codes': unknown, **body}
    if changed or not os.path.exists(live_path):
        json.dump(live, open(live_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        json.dump({'codes': codes, 'digest': digest, 'b': boxes}, open(os.path.join(a.out, 'boxes.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    valid = sum(nat['v'])
    print(f"{'CHANGED' if changed else 'UNCHANGED'} test_env={test_env} cec_time={cec_time} localities={len(locs)} boxes={nat['boxes']} valid={valid}")


if __name__ == '__main__':
    main()
