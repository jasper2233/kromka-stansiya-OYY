#!/usr/bin/env python3
# mes_server.py — SINOV MES SERVERI
#
# Ishga tushirish (shu papkada stansiya.html va tablo.html ham bo'lsin):
#     python mes_server.py
#
# Keyin brauzerda:
#     http://localhost:8000          stansiya (Pico ga ulanadi, QR o'qiydi)
#     http://localhost:8000/tablo    jonli tablo (o'lchovlar, avariyalar, detallar)
#
# Ma'lumotlar mes.db faylida saqlanadi (SQLite). O'chirsangiz — toza boshlanadi.
# Tashqi kutubxona kerak emas.

import http.server, socketserver, json, sqlite3, os, sys
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date, timedelta, timezone

PORT = 8000
BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, 'mes.db')

DEMO_PARTS = [
    ('A-1001', 'Yon panel',  800, 600, '2,2'),
    ('A-1002', 'Polka',     2750, 300, '2,0'),
    ('A-1003', 'Fasad',      716, 396, '2,2'),
    ('A-1004', 'Tsokol',     180,  80, '1,0'),
    ('ETALON', 'Etalon detal', 2750, 300, '1,0'),
]


def q(sql, args=(), one=False, commit=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, args)
        if commit:
            con.commit()
            return None
        return cur.fetchone() if one else cur.fetchall()
    finally:
        con.close()


def init():
    con = sqlite3.connect(DB)
    con.executescript('''
      CREATE TABLE IF NOT EXISTS events(
        id TEXT PRIMARY KEY, ts TEXT, station TEXT, type TEXT, data TEXT);
      CREATE TABLE IF NOT EXISTS parts(
        code TEXT PRIMARY KEY, name TEXT, L REAL, W REAL, need TEXT);
      CREATE TABLE IF NOT EXISTS settings(
        station TEXT PRIMARY KEY, data TEXT);
      CREATE INDEX IF NOT EXISTS ev_ts ON events(ts);
      CREATE TABLE IF NOT EXISTS stansiya(
        station TEXT PRIMARY KEY, oxirgi TEXT);
    ''')
    for p in DEMO_PARTS:
        con.execute('INSERT OR IGNORE INTO parts VALUES (?,?,?,?,?)', p)
    con.commit()
    con.close()


# Stansiya har 60 s /api/settings so'raydi — bu uning "tirikman" belgisi.
# JIM_S dan uzoq so'ramasa: kompyuter/Chrome/Pico o'chiq — stanok o'chiq deb hisoblanadi.
JIM_S = 180


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ' % (dt.microsecond // 1000)


def vaqt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def stansiya_kordi(st):
    """Stansiya ko'rindi. Oldingi ko'rinishdan JIM_S dan ko'p o'tgan bo'lsa —
    o'sha oraliqda stansiya ham, Pico ham bo'lmagan: jurnalga "o'chiq" yoziladi."""
    hozir = datetime.now(timezone.utc)
    r = q('SELECT oxirgi FROM stansiya WHERE station=?', (st,), one=True)
    if r:
        old = vaqt(r['oxirgi'])
        if (hozir - old).total_seconds() > JIM_S:
            ts = iso(old + timedelta(seconds=60))
            ev = {'id': 'srv-%s-%s' % (st, ts), 'station': st, 'ts': ts, 'type': 'pico',
                  'holat': 0, 'manba': 'server'}
            q('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)',
              (ev['id'], ts, st, 'pico', json.dumps(ev, ensure_ascii=False)), commit=True)
    q('INSERT OR REPLACE INTO stansiya VALUES (?,?)', (st, iso(hozir)), commit=True)


def stansiya_jim(st=None):
    """Stansiya hozir jimmi — (True/False, oxirgi ko'ringan vaqt ISO)."""
    if st:
        r = q('SELECT oxirgi FROM stansiya WHERE station=?', (st,), one=True)
    else:
        r = q('SELECT MAX(oxirgi) oxirgi FROM stansiya', one=True)
    if not r or not r['oxirgi']:
        return False, None
    return (datetime.now(timezone.utc) - vaqt(r['oxirgi'])).total_seconds() > JIM_S, r['oxirgi']


class H(http.server.BaseHTTPRequestHandler):

    def _send(self, code, body, ctype='application/json'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Station-Token')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _file(self, name):
        p = os.path.join(BASE, name)
        if not os.path.exists(p):
            return self._send(404, '<h2>%s topilmadi — mes_server.py bilan bir papkaga qo\'ying</h2>' % name, 'text/html')
        with open(p, 'rb') as f:
            self._send(200, f.read(), 'text/html')

    def _body(self):
        n = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(n) if n else b'{}'
        return json.loads(raw or b'{}')

    def do_OPTIONS(self):
        self._send(204, '')

    def do_GET(self):
        u = urlparse(self.path)
        p = parse_qs(u.query)

        if u.path in ('/', '/stansiya', '/stansiya.html', '/stansiya/'):
            return self._file('stansiya.html')
        if u.path in ('/tablo', '/tablo.html'):
            return self._file('tablo.html')

        if u.path == '/api/part':
            code = p.get('qr', [''])[0].strip().upper()
            r = q('SELECT * FROM parts WHERE code=?', (code,), one=True)
            if r:
                return self._send(200, dict(r))
            return self._send(404, {'error': 'topilmadi', 'code': code})

        if u.path == '/api/parts':
            return self._send(200, [dict(r) for r in q('SELECT * FROM parts ORDER BY code')])

        if u.path == '/api/settings':
            st = p.get('station', ['KROMKA-01'])[0]
            stansiya_kordi(st)
            r = q('SELECT data FROM settings WHERE station=?', (st,), one=True)
            return self._send(200, json.loads(r['data']) if r else {})

        if u.path == '/api/recent':
            n = int(p.get('n', ['60'])[0])
            typ = p.get('type', [None])[0]
            if typ:
                rows = q('SELECT * FROM events WHERE type=? ORDER BY ts DESC LIMIT ?', (typ, n))
            else:
                rows = q('SELECT * FROM events ORDER BY ts DESC LIMIT ?', (n,))
            out = []
            for r in rows:
                d = dict(r)
                d['data'] = json.loads(d['data'])
                out.append(d)
            return self._send(200, out)

        if u.path == '/api/stats':
            today = date.today().isoformat()
            olch = q("SELECT COUNT(*) c FROM events WHERE type='olchov' AND ts LIKE ?", (today + '%',), one=True)['c']
            nomos = q("SELECT COUNT(*) c FROM events WHERE type='olchov' AND ts LIKE ? AND data LIKE '%\"verdict\": \"NOMOS\"%'", (today + '%',), one=True)['c']
            ogoh = q("SELECT COUNT(*) c FROM events WHERE type='ogoh' AND ts LIKE ?", (today + '%',), one=True)['c']
            usk = q("SELECT data FROM events WHERE type='uskuna' ORDER BY ts DESC LIMIT 1", one=True)
            tz = q("SELECT data FROM events WHERE type='tezlik' ORDER BY ts DESC LIMIT 1", one=True)
            pc = q("SELECT data FROM events WHERE type='pico' ORDER BY ts DESC LIMIT 1", one=True)
            jim, _ = stansiya_jim()
            usk_h = json.loads(usk['data']).get('holat') if usk else None
            if jim or (pc and json.loads(pc['data']).get('holat') == 0):
                stanok = "o'chiq"
            else:
                stanok = None if usk_h is None else ('ishlayapti' if usk_h else "to'xtagan")
            skanersiz = q("SELECT COUNT(*) c FROM events WHERE type='olchov' AND ts LIKE ? AND data LIKE '%\"verdict\": \"SKANERSIZ\"%'", (today + '%',), one=True)['c']
            return self._send(200, {
                'sana': today, 'olchovlar': olch, 'nomos': nomos, 'ogohlar': ogoh,
                'skaner': olch - skanersiz, 'skanersiz': skanersiz,
                'uskuna': usk_h, 'stanok': stanok,
                'tezlik': json.loads(tz['data']).get('v') if tz else None,
            })

        if u.path == '/api/olchovlar':
            # tur=skaner — QR skanerlangan detallar, tur=skanersiz — skanersiz o'tganlar
            n = int(p.get('n', ['200'])[0])
            tur = p.get('tur', [''])[0]
            shart = ''
            if tur == 'skaner':
                shart = " AND data NOT LIKE '%\"verdict\": \"SKANERSIZ\"%'"
            elif tur == 'skanersiz':
                shart = " AND data LIKE '%\"verdict\": \"SKANERSIZ\"%'"
            rows = q("SELECT * FROM events WHERE type='olchov'" + shart + " ORDER BY ts DESC LIMIT ?", (n,))
            out = []
            for r in rows:
                d = dict(r)
                d['data'] = json.loads(d['data'])
                out.append(d)
            return self._send(200, out)

        if u.path == '/api/jurnal':
            # Stanok ish jurnali: uskuna (RUN kirishi) va pico (stansiya-Pico aloqasi)
            # hodisalaridan oraliqlar. Pico bilan aloqa yo'q = tok yo'q yoki kabel uzilgan.
            soat = float(p.get('soat', ['24'])[0])
            st = p.get('station', [None])[0]
            dan = (datetime.now(timezone.utc) - timedelta(hours=soat)).strftime('%Y-%m-%dT%H:%M:%S')
            sql = "SELECT ts, station, type, data FROM events WHERE type IN ('uskuna','pico') AND ts >= ?"
            args = [dan]
            if st:
                sql += ' AND station=?'
                args.append(st)
            rows = q(sql + ' ORDER BY ts', tuple(args))
            usk, pico, holat, bosh, oraliq = None, None, None, None, []
            for r in rows:
                d = json.loads(r['data'])
                if r['type'] == 'uskuna':
                    usk = d.get('holat')
                else:
                    pico = d.get('holat')
                h = "o'chiq" if pico == 0 else ('ishladi' if usk == 1 else ("to'xtadi" if usk == 0 else None))
                if h is not None and h != holat:
                    if holat is not None:
                        oraliq.append({'holat': holat, 'dan': bosh, 'gacha': r['ts']})
                    holat, bosh = h, r['ts']
            jim, oxirgi = stansiya_jim(st)
            if jim and holat != "o'chiq":
                # stansiya hozir ko'rinmayapti — oxirgi ko'ringanidan beri o'chiq
                ochiq_dan = iso(vaqt(oxirgi) + timedelta(seconds=60))
                if holat is not None:
                    oraliq.append({'holat': holat, 'dan': bosh, 'gacha': ochiq_dan})
                holat, bosh = "o'chiq", ochiq_dan
            if holat is not None:
                oraliq.append({'holat': holat, 'dan': bosh, 'gacha': None})
            oraliq.reverse()
            return self._send(200, oraliq)

        return self._send(404, {'error': 'yo\'q'})

    def do_POST(self):
        u = urlparse(self.path)

        if u.path == '/api/events':
            b = self._body()
            acks = []
            for ev in b.get('events', []):
                if 'id' not in ev:
                    continue
                q('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)',
                  (ev['id'], ev.get('ts') or datetime.now().isoformat(timespec='milliseconds'),
                   ev.get('station', ''), ev.get('type', ''), json.dumps(ev, ensure_ascii=False)),
                  commit=True)
                acks.append(ev['id'])
            return self._send(200, {'ack': acks})

        if u.path == '/api/parts':
            b = self._body()
            try:
                q('INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?)',
                  (b['code'].strip().upper(), b.get('name', ''), float(b['L']), float(b['W']),
                   b.get('need', '2,2')), commit=True)
                return self._send(200, {'ok': 1})
            except (KeyError, ValueError) as e:
                return self._send(400, {'error': str(e)})

        if u.path == '/api/parts/delete':
            b = self._body()
            q('DELETE FROM parts WHERE code=?', (b.get('code', '').strip().upper(),), commit=True)
            return self._send(200, {'ok': 1})

        if u.path == '/api/settings':
            b = self._body()
            st = b.get('station', 'KROMKA-01')
            b['updated'] = datetime.now().isoformat(timespec='seconds')
            q('INSERT OR REPLACE INTO settings VALUES (?,?)', (st, json.dumps(b, ensure_ascii=False)), commit=True)
            return self._send(200, {'ok': 1, 'updated': b['updated']})

        if u.path == '/api/clear':
            q('DELETE FROM events', commit=True)
            return self._send(200, {'ok': 1})

        return self._send(404, {'error': 'yo\'q'})

    def log_message(self, fmt, *a):
        msg = fmt % a
        if '/api/recent' in msg or '/api/stats' in msg:
            return
        if sys.stdout is None:  # pythonw — konsol yo'q
            return
        sys.stdout.write('  ' + msg + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    init()
    print('')
    print('  ================================================')
    print('  SINOV MES SERVERI ishlayapti')
    print('  Stansiya : http://localhost:%d' % PORT)
    print('  Tablo    : http://localhost:%d/tablo' % PORT)
    print('  Baza     : %s' % DB)
    print('  To\'xtatish: Ctrl+C')
    print('  ================================================')
    print('')
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('0.0.0.0', PORT), H) as s:
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print('\n  to\'xtatildi')
