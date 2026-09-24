# -*- coding: utf-8 -*-
# Stansiya tirikmi, Pico ulandimi, MES ga nima kelyapti — qisqa tekshiruv.
import json, urllib.request

MES = 'http://localhost:8000'

with urllib.request.urlopen(MES + '/api/recent?n=12', timeout=10) as r:
    rows = json.load(r)
print('--- oxirgi hodisalar ---')
for e in rows:
    d = e['data']
    qosh = ''
    if e['type'] == 'olchov':
        qosh = '%.1f mm %s' % (d.get('measured_mm') or 0, d.get('verdict', ''))
    elif e['type'] in ('pico', 'uskuna'):
        qosh = 'holat=%s' % d.get('holat')
    print(' ', e['ts'], e['type'], qosh)

with urllib.request.urlopen(MES + '/api/stats', timeout=10) as r:
    print('--- stats ---', json.load(r))
