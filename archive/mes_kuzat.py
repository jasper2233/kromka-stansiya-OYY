import json, time, urllib.request
MES = 'http://localhost:8000'
korilgan = set(); t0 = time.time(); boshi = time.strftime('%Y-%m-%dT%H:%M', time.gmtime())
while time.time() - t0 < 900:
    try:
        rows = json.load(urllib.request.urlopen(MES + '/api/recent?n=50', timeout=10))
        for e in reversed(rows):
            k = (e['ts'], e['type'], json.dumps(e['data'], sort_keys=True))
            if e['ts'] < boshi or k in korilgan: continue
            korilgan.add(k); d = e['data']
            q = {'olchov': lambda: '%s mm %s kod=%s farq=%s v=%s xotiradan=%s' % (d.get('measured_mm'), d.get('verdict'), d.get('kod'), d.get('farq'), d.get('v_olch'), d.get('xotiradan', '')),
                 }.get(e['type'], lambda: json.dumps(d, ensure_ascii=False)[:200])()
            print(e['ts'][11:19], e['type'], q, flush=True)
    except Exception as x:
        print(time.strftime('%H:%M:%S'), 'MES XATO', x, flush=True)
    time.sleep(10)
print('TUGADI', flush=True)
