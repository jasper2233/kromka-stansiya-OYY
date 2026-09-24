# -*- coding: utf-8 -*-
# MES sozlamasida avariya ovozini yoqish (AV=1). Boshqa qiymatlar tegilmaydi.
import json, urllib.request

MES = 'http://localhost:8000'
ST = 'KROMKA-01'

with urllib.request.urlopen(MES + '/api/settings?station=' + ST, timeout=10) as r:
    s = json.load(r)
print('oldingi kal:', s.get('kal'))

s.setdefault('kal', {})['AV'] = 1
req = urllib.request.Request(MES + '/api/settings',
                             data=json.dumps(s, ensure_ascii=False).encode('utf-8'),
                             headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as r:
    print('javob:', json.load(r))

with urllib.request.urlopen(MES + '/api/settings?station=' + ST, timeout=10) as r:
    print('yangi kal:', json.load(r).get('kal'))
