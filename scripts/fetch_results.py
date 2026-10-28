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


def parse_page_national(html):
    """Read the national totals off the Committee's results page (used when the CSV files are not published yet)."""
    t = re.sub(r'<(\w+)[^>]*>', r'<\1>', re.sub(r'\s+', ' ', html))
    def total(label):
        m = re.search(re.escape(label) + r'\s*</div>\s*<div>\s*([\d,]+)', t)
        return int(m.group(1).replace(',', '')) if m else None
    rows = re.findall(r'<td>\s*([\u05d0-\u05ea]{1,4})\s*</td>\s*<td>\s*[\d.]+%\s*</td>\s*<td>\s*<div>\s*<span>\s*([\d,]+)\s*</span>', t)
    votes = {code: int(n.replace(',', '')) for code, n in rows}
    return {'eligible': total('מספר בעלי זכות בחירה'), 'votes': total('קולות עד עתה'), 'boxes': total('קלפיות עד עתה'),
            'valid': total('קולות כשרים עד עתה'), 'invalid': total('קולות פסולים עד עתה'), 'parties': votes}


def num(x):
    try:
        return int(float(str(x).strip() or 0))
    except ValueError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--local', help='read expc.csv/expb.csv (and page.html if present) from this folder instead of downloading')
    ap.add_argument('--guard', action='store_true', help='with --local: apply the polls-closed and test-site checks, as for real downloads')
    ap.add_argument('--out', default=os.path.join(ROOT, 'data'))
    a = ap.parse_args()

    tracked = [p['code'] for p in CFG['parties']]
    polls_close = datetime.strptime(CFG['polls_close_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    before_close = datetime.now(timezone.utc) < polls_close
    codes = tracked + ['OTHER']
    cec_time, test_env = None, False
    html = None
    if a.local:
        have_csv = os.path.exists(os.path.join(a.local, 'expc.csv')) and os.path.exists(os.path.join(a.local, 'expb.csv'))
        expc = open(os.path.join(a.local, 'expc.csv'), 'rb').read() if have_csv else None
        expb = open(os.path.join(a.local, 'expb.csv'), 'rb').read() if have_csv else None
        test_env = os.path.exists(os.path.join(a.local, 'TEST'))
        page = os.path.join(a.local, 'page.html')
        if os.path.exists(page):
            html = open(page, encoding='utf-8', errors='replace').read()
            test_env = test_env or 'סביבת בדיקות' in html
            m = re.search(r'תוצאות נכון ל-\s*([0-9/]+\s+[0-9:]+)', html)
            cec_time = m.group(1) if m else None
        stamp = os.path.join(a.local, 'cec_time.txt')
        if not cec_time and os.path.exists(stamp):
            cec_time = open(stamp, encoding='utf-8').read().strip() or None
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

    page_only = expc is None
    if page_only:
        # The Committee posts its results page before its CSV files. Until the files appear,
        # publish the national totals as one row with no locality breakdown.
        if not html:
            sys.exit('No CSV files and no results page in the upload.')
        pn = parse_page_national(html)
        if not pn['parties'] or not pn['boxes']:
            sys.exit('The results page has no counted ballot boxes yet.')
        v = [0] * len(codes)
        for p, n in pn['parties'].items():
            v[codes.index(p) if p in tracked else len(codes) - 1] += n
        crow, brow, pc, pb = [], [], [], []
        page_row = [9998, 'ארצי', 0, pn['votes'] or 0, pn['invalid'] or 0, pn['boxes'], v]
    nb = {}
    boxes = {}
    muni, est_boxes = None, {}
    if a.local and os.path.exists(os.path.join(a.local, 'municipal_data.json')):
        # The mirror's town-by-town file, built from the Committee's locality results, often runs ahead
        # of its expc.csv copy. Same columns as expc.csv, keyed by locality code.
        muni = json.load(open(os.path.join(a.local, 'municipal_data.json'), encoding='utf-8'))
    if not page_only:
        _, pc, crow = parse(expc)
        _, pb, brow = parse(expb)
    if muni and muni.get('features'):
        crow = [{**f, 'סמל ישוב': code} for code, f in muni['features'].items()]
        pc = [p for p in muni.get('parties', []) if p and p not in META_COLS]
        # The town file has no per-town box count, and expb.csv may lag it. Estimate each town's counted
        # boxes from the share of its registered voters already counted, never below expb.csv's count.
        base = json.load(open(os.path.join(ROOT, 'data', 'localities.json'), encoding='utf-8'))['locs']
        tot = {l['c']: (l.get('nb') or 0, l.get('r') or 0) for l in base}
        for d in crow:
            c = num(d['סמל ישוב']); N, R = tot.get(c, (0, 0))
            if N and R and num(d.get('מצביעים')):
                est_boxes[c] = min(N, max(1, round(N * num(d.get('בזב')) / R)))
    for d in brow:
        c = num(d['סמל ישוב'])
        if num(d.get('מצביעים')) == 0 and num(d.get('כשרים')) == 0:
            continue  # box listed but not counted yet
        nb[c] = nb.get(c, 0) + 1
        boxes.setdefault(str(c), []).append([d.get('קלפי', '').strip(), num(d.get('בזב')), num(d.get('מצביעים')), num(d.get('פסולים')), vec(d, pb)])
    for c, n in est_boxes.items():
        nb[c] = max(nb.get(c, 0), n)
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
    if muni and muni.get('features'):
        # Ballot-box detail (expb.csv) may lag the town file; use the town file's own count.
        nat['boxes'] = (muni.get('totals') or {}).get('kalpi_counted') or nat['boxes']
    if page_only:
        # Keep the latest town-by-town data already published (for example from the mirror) and add
        # whatever the Committee's page counts beyond it as one row, so national totals match the page.
        prev_path = os.path.join(a.out, 'live.json')
        prev_live = json.load(open(prev_path, encoding='utf-8')) if os.path.exists(prev_path) else {}
        base = []
        if prev_live.get('codes') == codes and not prev_live.get('test_env'):
            base = [row for row in prev_live.get('locs', []) if row[0] != 9998]
        bt = sum(r[3] for r in base); bx = sum(r[4] for r in base); bb = sum(r[5] for r in base); br = sum(r[2] for r in base)
        bv = [sum(r[6][k] for r in base) for k in range(len(codes))]
        rv = [max(0, p - q) for p, q in zip(page_row[6], bv)]
        rt, rx, rb = max(0, page_row[3] - bt), max(0, page_row[4] - bx), max(0, page_row[5] - bb)
        rr = round(rt * br / bt) if bt else 0  # registered voters estimated at the counted towns' turnout
        locs = base + ([[9998, 'ארצי', rr, rt, rx, rb, rv]] if rb or sum(rv) else [])
        nat = {'r': br + rr, 't': bt + rt, 'x': bx + rx, 'v': [p + q for p, q in zip(bv, rv)], 'boxes': bb + rb}
        pc = list(pn['parties'])
    unknown = sorted(set(pc) - set(tracked))
    if not a.local or a.guard:
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
            'other_codes': unknown, 'page_only': page_only, **body}
    if changed or not os.path.exists(live_path):
        json.dump(live, open(live_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        if not page_only:  # a page upload has no ballot-box detail; keep the last box file
            json.dump({'codes': codes, 'digest': digest, 'b': boxes}, open(os.path.join(a.out, 'boxes.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    valid = sum(nat['v'])
    print(f"{'CHANGED' if changed else 'UNCHANGED'} test_env={test_env} cec_time={cec_time} localities={len(locs)} boxes={nat['boxes']} valid={valid}")


if __name__ == '__main__':
    main()
