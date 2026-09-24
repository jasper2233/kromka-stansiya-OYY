# sinov_pc.py — main.py mantiqini KOMPYUTERDA sinash (Pico kerak emas)
#
# Ishga tushirish:  python pico/sinov_pc.py
#
# machine / time / select modullari soxta (virtual vaqt) bilan almashtiriladi,
# main.py o'zgartirilmasdan import qilinadi va qadam() chaqiriladi. Lenta,
# detallar, datchiklar, RUN va 18 m/min kirishlari modellashtiriladi.
# Har ssenariy natijasini (o'lchov, ogoh, avariya) kutilgani bilan solishtiradi.

import sys, os, types, json

# ---------------- soxta apparat ----------------
SOAT = {'us': 0}

def _ticks_us(): return SOAT['us']
def _ticks_ms(): return SOAT['us'] // 1000
def _ticks_diff(a, b): return a - b
def _ticks_add(a, b): return a + b
def _sleep_ms(n): pass

vaqt = types.ModuleType('time')
vaqt.ticks_us = _ticks_us; vaqt.ticks_ms = _ticks_ms
vaqt.ticks_diff = _ticks_diff; vaqt.ticks_add = _ticks_add
vaqt.sleep_ms = _sleep_ms

PINLAR = {}

class Pin:
    IN = 0; OUT = 1; PULL_UP = 2; IRQ_FALLING = 4; IRQ_RISING = 8
    def __init__(self, id, mode=0, pull=None, value=None):
        self.id = id; self._v = 1 if value is None else value; self.h = None
        PINLAR[id] = self
    def value(self, v=None):
        if v is None:
            return self._v
        self._v = v
    def irq(self, trigger=0, handler=None):
        self.h = handler
    def qoy(self, v):                     # tashqi signal — chekka bo'lsa IRQ
        if v != self._v:
            self._v = v
            if self.h:
                self.h(self)

machine = types.ModuleType('machine')
machine.Pin = Pin

class _Poll:
    def register(self, *a): pass
    def poll(self, t=0): return []
select_m = types.ModuleType('select')
select_m.poll = _Poll; select_m.POLLIN = 1

sys.modules['machine'] = machine
sys.modules['select'] = select_m
_asl_time = sys.modules.get('time')
sys.modules['time'] = vaqt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CHIQ = []
import builtins
_asl_print = builtins.print
builtins.print = lambda *a, **k: None       # main.py ning Thonny matni jim
import main as M
builtins.print = _asl_print
sys.modules['time'] = _asl_time

ASL_YUBOR = M.yubor
ASL_BUYRUQ = M.buyruq_tekshir
import tempfile
M.KAL_FAYL = os.path.join(tempfile.gettempdir(), 'kromka_sinov_kal.json')
M.yubor = lambda d: CHIQ.append(json.loads(json.dumps(d)))
M.chop = lambda s: None
M.CHOP = False
BUYRUQ = []
def _buyruq():
    while BUYRUQ:
        q = BUYRUQ.pop(0).split()
        if q[0] == 'STOP': M.avariya_toxtat()
        elif q[0] == 'SET':
            for kv in q[1:]:
                k, v = kv.split('='); M.KAL[k] = float(v)
M.buyruq_tekshir = _buyruq

# ---------------- lenta modeli ----------------
D_HAQ = 2553.37     # haqiqiy datchiklar orasi, mm

class Lenta:
    def __init__(self):
        self.detal = []           # [old_qirra_x, L]; D1 x=0, D2 x=D_HAQ
        self.run = False; self.v18 = False
        self.d2_kor = True
        self.tiq = False          # tiqilish: stanok yonib turibdi, lekin detal yurmayapti
        self.pin_run(); self.datchik()
    def v_mm_s(self):
        if self.tiq:
            return 0.0
        if not self.run and not self.v18:
            return 0.0
        return (18.227 if self.v18 else 10.151) * 1000 / 60
    def pin_run(self):
        PINLAR[M.GP_RUN].qoy(0 if self.run else 1)
        PINLAR[M.GP_V18].qoy(0 if self.v18 else 1)
    def datchik(self):
        def yop(x):
            return any(f - L < x <= f for f, L in self.detal)
        PINLAR[M.GP_D1].qoy(0 if yop(0.0) else 1)
        PINLAR[M.GP_D2].qoy(0 if (yop(D_HAQ) and self.d2_kor) else 1)
    def yur(self, ms):
        for _ in range(int(ms)):
            SOAT['us'] += 1000
            v = self.v_mm_s() / 1000.0
            for d in self.detal:
                d[0] += v
            self.detal = [d for d in self.detal if d[0] - d[1] < D_HAQ + 500]
            self.datchik()
            if SOAT['us'] % 5000 == 0:
                M.qadam()
    def qoy(self, L, old=-50.0):
        self.detal.append([old, L])

def yangi_holat():
    CHIQ.clear(); BUYRUQ.clear()
    M.navbat.clear(); M.kutuv.clear(); M.xotira.clear()
    for k in (1, 2):
        M.kuzat[k].update({'us': None, 'ms': None, 'yopiq': False, 'stuck': False, 'bekor': False})
    M.kuzat[2]['juft_d1'] = False
    M.xato.update({1: 0, 2: 0}); M.iflos.update({1: 0, 2: 0})
    M.USK.update({'holat': None, 'xom': None, 't': 0})
    M.AL.update({'rejim': 'IDLE', 't0': 0})
    M.KAL.update({'D': D_HAQ, 'V10': 10.151, 'V18': 18.227, 'K1': 0.0, 'K2': 0.0,
                  'B1': 0.0, 'B2': 0.0, 'C': 0.0, 'TD': 12.0, 'AO': 0.0, 'HQ': 2500.0, 'HA': 1500.0, 'AV': 1.0})
    for p in PINLAR.values():
        if p.id in (M.GP_D1, M.GP_D2, M.GP_RUN, M.GP_V18):
            p._v = 1
    SOAT['us'] += 10_000_000
    return Lenta()

def olchovlar(): return [e for e in CHIQ if e['ev'] == 'olchov']
def ogohlar(): return [e for e in CHIQ if e['ev'] == 'ogoh']
def toxtashlar(): return [e for e in CHIQ if e['ev'] == 'avariya_toxtash']
def avariya_yoniq(): return M.AL['rejim'] == 'AVARIYA'

def yetib_bor(l, x, ms_max=120000):
    """Detal old qirrasi x ga yetguncha yurgizish (birinchi detal)."""
    for _ in range(ms_max // 5):
        if l.detal and l.detal[0][0] >= x:
            return
        l.yur(5)
    raise RuntimeError('yetib bormadi')

# ---------------- ssenariylar ----------------
NATIJA = []

def tekshir(nom, shart, izoh=''):
    if izoh is CHIQ:
        izoh = [e for e in CHIQ if e['ev'] not in ('holat', 'tezlik')]
    NATIJA.append((nom, bool(shart), izoh))

def S01():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(300); l.yur(25000)
    o = olchovlar()
    tekshir('01 300 mm 10 m/min oddiy', len(o) == 1 and o[0]['kod'] == 'OK' and abs(o[0]['L'] - 300) < 2 and not avariya_yoniq(), o)

def S02():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(2740); l.yur(40000)
    o = olchovlar()
    tekshir('02 2740 mm 10 m/min (L > D)', len(o) == 1 and o[0]['kod'] == 'OK' and abs(o[0]['L'] - 2740) < 2 and not toxtashlar(), o)

def S03():
    l = yangi_holat(); l.v18 = True; l.run = True; l.pin_run(); l.yur(300)
    l.qoy(2740); l.yur(25000)
    o = olchovlar()
    tekshir('03 2740 mm 18 m/min', len(o) == 1 and o[0]['kod'] == 'OK' and abs(o[0]['L'] - 2740) < 2, o)

def S04():
    l = yangi_holat(); l.v18 = True; l.run = True; l.pin_run(); l.yur(300)
    for i in range(6):
        l.qoy(300, old=-50 - i * 450)
    l.yur(25000)
    o = olchovlar()
    tekshir('04 6 ta 300 mm ketma-ket, 150 mm oraliq', len(o) == 6 and all(e['kod'] == 'OK' and abs(e['L'] - 300) < 2 for e in o) and not avariya_yoniq(), [e['L'] for e in o])

def S05():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(600, old=-50); l.qoy(2740, old=-850); l.qoy(300, old=-3800)
    l.yur(60000)
    o = olchovlar()
    tekshir('05 aralash 600, 2740, 300', [round(e['L']) for e in o] in ([600, 2740, 300], [599, 2740, 300], [600, 2739, 300], [600, 2740, 299], [600, 2740, 301], [601, 2740, 300], [600, 2741, 300]) and all(e['kod'] == 'OK' for e in o), [e['L'] for e in o])

def S06():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(1000)
    l.run = False; l.pin_run(); l.yur(3000)
    tekshir('06 yo\'lda detal yo\'q — to\'xtash avariyasiz', not toxtashlar() and not avariya_yoniq(), CHIQ)

def S07():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 200)
    l.run = False; l.pin_run(); l.yur(3000)
    t = toxtashlar()
    ok1 = len(t) == 1 and t[0]['d1'] == 1 and t[0]['d2'] == 0 and t[0]['oraliq'] == 0 and avariya_yoniq()
    l.detal.clear(); l.yur(2000)             # operator detalni orqaga tortib oldi
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(30000)
    tekshir('07 1-holat: D1 da, stop, detal olib tashlandi', ok1 and not olchovlar() and not ogohlar() and not avariya_yoniq(), CHIQ)

def S08():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 200)
    l.run = False; l.pin_run(); l.yur(5000)
    l.run = True; l.pin_run(); l.yur(40000)
    t = toxtashlar()
    tekshir('08 1-holat: D1 da, stop, qayta yonib detal o\'tib ketdi', len(t) == 1 and t[0]['d1'] == 1 and not olchovlar() and not ogohlar(), CHIQ)

def S09():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(2740); yetib_bor(l, D_HAQ + 100)
    l.run = False; l.pin_run(); l.yur(5000)
    t = toxtashlar()
    ok1 = len(t) == 1 and t[0]['d1'] == 1 and t[0]['d2'] == 1 and t[0]['birga'] == 1 and avariya_yoniq()
    l.run = True; l.pin_run(); l.yur(40000)
    tekshir('09 2-holat: 2740 mm D1 va D2 da, stop, qayta yondi', ok1 and not olchovlar() and not ogohlar(), CHIQ)

def S10():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(800); yetib_bor(l, D_HAQ + 300)
    l.run = False; l.pin_run(); l.yur(5000)
    t = toxtashlar()
    ok1 = len(t) == 1 and t[0]['d1'] == 0 and t[0]['d2'] == 1 and t[0]['oraliq'] == 0
    l.run = True; l.pin_run(); l.yur(20000)
    tekshir('10 3-holat: D1 dan o\'tgan, D2 da, stop', ok1 and not olchovlar() and not ogohlar(), CHIQ)

def S11():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(800); yetib_bor(l, 1800)
    l.run = False; l.pin_run(); l.yur(8000)
    t = toxtashlar()
    ok1 = len(t) == 1 and t[0]['d1'] == 0 and t[0]['d2'] == 0 and t[0]['oraliq'] == 1 and avariya_yoniq()
    l.run = True; l.pin_run(); l.yur(40000)
    tekshir('11 4-holat: D1 dan o\'tgan, D2 ga yetmagan (oraliqda), stop', ok1 and not olchovlar() and not ogohlar(), CHIQ)

def S12():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(300, old=-50); l.qoy(300, old=-1250); l.qoy(300, old=-2500)
    yetib_bor(l, D_HAQ + 100)                # 1-si D2 da, 2-si oraliqda, 3-si D1 da
    l.run = False; l.pin_run(); l.yur(4000)
    t = toxtashlar()
    ok1 = len(t) == 1 and t[0]['d1'] == 1 and t[0]['d2'] == 1 and t[0]['oraliq'] == 1 and t[0]['birga'] == 0
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(40000)
    ok2 = not olchovlar() and not ogohlar()
    l.qoy(700); l.yur(40000)                 # keyingi toza detal
    o = olchovlar()
    tekshir('12 uchta detal (D2, oraliq, D1), stop; keyin yangi detal o\'lchanadi', ok1 and ok2 and len(o) == 1 and abs(o[0]['L'] - 700) < 2 and o[0]['kod'] == 'OK' and not ogohlar(), CHIQ)

def S13():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(2740); yetib_bor(l, D_HAQ + 100)
    l.run = False; l.pin_run(); l.yur(3000)
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(40000)
    l.qoy(1000); l.yur(40000)
    o = olchovlar()
    tekshir('13 2-holatdan keyin yangi 1000 mm to\'g\'ri o\'lchanadi', len(o) == 1 and abs(o[0]['L'] - 1000) < 2 and not ogohlar() and not avariya_yoniq(), CHIQ)

def S14():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 300)
    l.run = False; l.pin_run(); SOAT['us'] += 0; l.run = True
    # 100 ms uzilish (lenta modeli to'xtamaydi — faqat kirish signali)
    PINLAR[M.GP_RUN].qoy(1); l.yur(100); PINLAR[M.GP_RUN].qoy(0)
    l.yur(40000)
    o = olchovlar()
    tekshir('14 RUN signalida 100 ms uzilish — avariya emas, o\'lchov bor', not toxtashlar() and len(o) == 1 and abs(o[0]['L'] - 1500) < 2, CHIQ)

def S15():
    l = yangi_holat(); M.KAL['AO'] = 1.0; l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 300)
    l.run = False; l.pin_run(); l.yur(3000)
    tekshir('15 AO=1: hodisa yuboriladi, lampa/sirena yo\'q', len(toxtashlar()) == 1 and not avariya_yoniq() and not PINLAR[M.GP_RELE].value() == M.RELE_YOQ, CHIQ)

def S16():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 300)
    l.run = False; l.pin_run(); l.yur(20000)
    ok1 = avariya_yoniq()
    l.run = True; l.pin_run(); l.yur(3000)
    ok2 = avariya_yoniq()                     # qayta yonsa ham davom etadi
    BUYRUQ.append('STOP'); l.yur(100)
    tekshir('16 avariya STOP gacha davom etadi (qayta yonsa ham)', ok1 and ok2 and not avariya_yoniq(), '')

def S17():
    l = yangi_holat(); l.yur(1000)                 # stanok o'chiq
    l.qoy(1200, old=300); l.yur(2000)            # operator detalni D1 ga qo'ydi
    l.run = True; l.pin_run(); l.yur(40000)
    tekshir('17 stanok o\'chiq paytda qo\'yilgan detal — bekor, avariyasiz', not olchovlar() and not ogohlar() and not toxtashlar() and not avariya_yoniq(), CHIQ)

def S18():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 300)
    l.run = False; l.pin_run(); l.yur(90000)     # 90 s turib qoldi
    tekshir('18 uzoq to\'xtash (90 s) — "yopishib qolgan" chiqmaydi', not ogohlar() and len(toxtashlar()) == 1, CHIQ)

def S19():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(800); yetib_bor(l, D_HAQ + 300)
    l.run = False; l.pin_run(); l.yur(3000)
    l.detal.clear(); l.yur(2000)                 # D2 dagi detal qo'lda olindi
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(2000)
    l.qoy(600); l.yur(40000)
    o = olchovlar()
    tekshir('19 D2 dan qo\'lda olindi, keyingi detal to\'g\'ri', len(o) == 1 and abs(o[0]['L'] - 600) < 2 and not ogohlar(), CHIQ)

def S20():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(2740); yetib_bor(l, D_HAQ + 100)
    l.run = False; l.pin_run(); l.yur(2000)
    l.detal[0][0] = D_HAQ - 50; l.yur(500)        # orqaga tortildi: avval D2 ochildi
    l.detal.clear(); l.yur(500)                  # keyin D1 ham
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(2000)
    l.qoy(900); l.yur(40000)
    o = olchovlar()
    tekshir('20 2740 orqaga tortib olindi, keyingi 900 mm to\'g\'ri', len(o) == 1 and abs(o[0]['L'] - 900) < 2 and not ogohlar(), CHIQ)

def S21():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1000); yetib_bor(l, 200)
    l.v18 = True; l.pin_run(); l.yur(30000)      # detal yo'lda 10 -> 18
    tekshir('21 tezlik 10->18 almashishi — avariya emas', not toxtashlar() and len(olchovlar()) == 1, CHIQ)

def S22():
    l = yangi_holat(); l.v18 = True; l.pin_run(); l.yur(300)   # faqat 18 kirishi (RUN yo'q)
    l.qoy(1000); yetib_bor(l, 200)
    l.v18 = False; l.pin_run(); l.yur(3000)
    tekshir('22 18 m/min rejimida (RUN siz) to\'xtash ham qayd qilinadi', len(toxtashlar()) == 1 and avariya_yoniq(), CHIQ)

def S23():
    # v1.17: D2 tasdiqlamaguncha D1 yozuvi navbatdan TUSHMAYDI. D2 ko'rmasa —
    # soxta o'lchov emas, ogohlantirish chiqadi (datchik javob bermayapti).
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.d2_kor = False
    l.qoy(500); l.yur(130000)
    og = [e for e in ogohlar() if e['sabab'] == 'javob_yoq']
    tekshir('23 D2 ko\'rmasa: yozuv navbatda qoladi, javob_yoq ogohi chiqadi',
            not olchovlar() and len(og) == 1 and len(M.kutuv) == 1 and not toxtashlar(), CHIQ)

def S24():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    PINLAR[M.GP_D1].h = PINLAR[M.GP_D1].h
    l.qoy(20000); yetib_bor(l, 100); l.yur(35000)    # juda uzun — yopishib qolish
    tekshir('24 stanok ishlayotganda yopishib qolish hali ham aniqlanadi', any(e['sabab'] == 'yopishib_qolgan' for e in ogohlar()), CHIQ)

def S25():
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(1500); yetib_bor(l, 1700)             # oraliqda
    l.run = False; l.pin_run(); l.yur(3000)
    BUYRUQ.append('STOP'); l.run = True; l.pin_run(); l.yur(200)
    l.qoy(400); l.yur(60000)                    # bekor detal ortidan yangi detal
    o = olchovlar()
    tekshir('25 oraliqdagi bekor detal ortidan kelgan detal to\'g\'ri juftlanadi', len(o) == 1 and abs(o[0]['L'] - 400) < 2 and not ogohlar(), CHIQ)

def _signal_yoz(ms):
    """ms davomida har 5 ms: (vaqt, lampa, GP16). v1.20 dan ovoz Pico da yo'q —
    GP16 doim past turishi ham tekshiriladi."""
    t = []
    for i in range(ms // 5):
        SOAT['us'] += 5000
        M.alarm_tick()
        t.append((i * 5, M.rele.value() == M.RELE_YOQ, M.audio.value()))
    return t

def _yonishlar(t, idx):
    b, old = [], False
    for q in t:
        if q[idx] and not old:
            b.append(q[0])
        old = q[idx]
    return b

def S26():
    yangi_holat(); M.signal(False); SOAT['us'] += 1000
    M.qr_boshla(); t = _signal_yoz(800)
    lam = _yonishlar(t, 1)
    tugadi = all(not q[1] for q in t if q[0] >= 505)
    jim = all(q[2] == 0 for q in t)
    tekshir('26 QR: 0.5 s da lampa 2 marta miltillaydi, GP16 jim', len(lam) == 2 and tugadi and jim and lam[1] - lam[0] in (245, 250, 255), (lam, jim))

def S27():
    yangi_holat(); M.signal(False); SOAT['us'] += 1000
    M.avariya_boshla(); t = _signal_yoz(6000)
    lam = _yonishlar(t, 1)
    jim = all(q[2] == 0 for q in t)
    M.avariya_toxtat()
    tekshir('27 AVARIYA: lampa 1 s yonadi / 1 s o\'chadi, GP16 jim', len(lam) >= 3 and lam[0] <= 5 and all(abs(b - a - 2000) <= 10 for a, b in zip(lam, lam[1:])) and jim and M.rele.value() != M.RELE_YOQ, lam)

def S28():
    yangi_holat(); M.signal(False); SOAT['us'] += 1000
    M.test_boshla(); t = _signal_yoz(1500)
    on = [q[0] for q in t if q[1]]
    jim = all(q[2] == 0 for q in t)
    tekshir('28 TEST: lampa 1 s, GP16 jim', on and on[-1] - on[0] >= 990 and on[-1] < 1005 and jim, (on[:1], on[-1:]))

def S29():
    # Stansiya ulanmagan: o'lchov xotiraga yig'iladi, HB kelganda eski_ms bilan chiqadi
    import io, builtins as B
    l = yangi_holat(); M.yubor = ASL_YUBOR
    M.yigilgan.clear(); M.XOST.update({'oxir': None, 'yoqolgan': 0})
    chiq = []; asl = B.print
    B.print = lambda *a, **k: chiq.append(' '.join(str(x) for x in a))
    try:
        l.run = True; l.pin_run(); l.yur(300)
        l.qoy(600); l.yur(25000)
        jim = [s for s in chiq if s.startswith('{')]
        n_xot = len(M.yigilgan)
        l.yur(10000)                                  # 10 s o'tdi
        M.poll = type('P', (), {'poll': lambda s, t=0: [1]})()
        M.sys.stdin = io.StringIO('HB\n')
        ASL_BUYRUQ()
        js = [json.loads(s) for s in chiq if s.startswith('{')]
    finally:
        B.print = asl; M.yubor = lambda d: CHIQ.append(json.loads(json.dumps(d)))
        M.XOST['oxir'] = None
    bosh = [j for j in js if j['ev'] == 'yigilgan']
    olch = [j for j in js if j['ev'] == 'olchov']
    tekshir('29 stansiyasiz: o\'lchov xotiraga, HB da eski_ms bilan chiqadi', not jim and n_xot >= 2 and bosh and len(olch) == 1 and abs(olch[0]['L'] - 600) < 2 and olch[0]['eski_ms'] >= 10000 and not M.yigilgan, js)

def _siglar():
    return [e for e in CHIQ if e['ev'] == 'sig']

def S30():
    # v1.20: ovoz MES tomonida. Pico har rele almashishida "sig" yuboradi —
    # MES tovushni shu xabardan boshlaydi, shuning uchun faza siljimaydi.
    yangi_holat(); M.signal(False); SOAT['us'] += 1000

    CHIQ.clear(); M.qr_boshla(); tq = _signal_yoz(600)
    sq = _siglar()
    qr_ok = ([e['on'] for e in sq] == [1, 0, 1, 0]
             and all(e['r'] == 'qr' for e in sq)
             and all(e['ms'] == M.QR_MS // 4 for e in sq if e['on'])
             and len(_yonishlar(tq, 1)) == sum(e['on'] for e in sq))

    CHIQ.clear(); M.avariya_boshla(); ta = _signal_yoz(4200)
    sa = _siglar()
    av_ok = ([e['on'] for e in sa] == [1, 0, 1, 0, 1]
             and all(e['r'] == 'avariya' for e in sa)
             and all(e['ms'] == M.AVARIYA_MS for e in sa if e['on'])
             and len(_yonishlar(ta, 1)) == sum(e['on'] for e in sa))

    CHIQ.clear(); M.avariya_toxtat()
    toxt_ok = [(e['r'], e['on']) for e in _siglar()] == [('idle', 0)]
    tekshir('30 sig hodisasi: rejim, uzunlik va lampa bilan bir lahzada',
            qr_ok and av_ok and toxt_ok, (sq, sa, _siglar()))

def S32():
    # AV/HQ/HA endi Pico da faqat SAQLANADI va qaytariladi — ovozni o'chirish yoki
    # chalish MES ning ishi. Pico tomonda AV=0 bo'lsa ham lampa va sig o'zgarmaydi.
    yangi_holat(); M.KAL['AV'] = 0.0; M.signal(False); SOAT['us'] += 1000
    CHIQ.clear(); M.avariya_boshla(); ta = _signal_yoz(4200); M.avariya_toxtat()
    lamp_a = len(_yonishlar(ta, 1)); sig_on = sum(e['on'] for e in _siglar())
    jim = all(q[2] == 0 for q in ta)
    tekshir('32 AV=0 Pico mantiqiga ta\'sir qilmaydi: lampa va sig o\'z ishida, GP16 jim',
            lamp_a >= 2 and sig_on == lamp_a and jim and M.KAL['AV'] == 0.0, (lamp_a, sig_on, jim))

def S31():
    # SET kelsa kal.json ga yoziladi, qayta yonganda o'qiladi
    import io
    yangi_holat()
    try: os.remove(M.KAL_FAYL)
    except OSError: pass
    M.poll = type('P', (), {'poll': lambda s, t=0: [1]})()
    M.sys.stdin = io.StringIO('SET D=2553.37 B1=-2.19 HQ=2600\n')
    ASL_BUYRUQ()
    M.KAL['D'] = 1.0; M.KAL['B1'] = 0.0; M.KAL['HQ'] = 1.0
    M.kal_yukla()
    M.XOST['oxir'] = None
    tekshir('31 sozlama fleshga yoziladi va qayta o\'qiladi', abs(M.KAL['D'] - 2553.37) < 1e-6 and M.KAL['B1'] == -2.19 and M.KAL['HQ'] == 2600.0, dict(M.KAL))

def tasodifiy(seed):
    """Tasodifiy ketma-ketlik: detallar + tasodifiy to'xtashlar, haqiqat bilan solishtirish.

    Detal to'xtash paytida D1 ga yetgan (old > 0) va D2 dan chiqmagan (orqa <= D)
    bo'lsa — bekor bo'lishi kerak, aks holda to'g'ri o'lchanishi kerak.
    """
    import random
    R = random.Random(seed)
    l = yangi_holat()
    l.v18 = R.random() < 0.5; l.run = not l.v18 or R.random() < 0.5; l.pin_run(); l.yur(500)
    detallar = []                 # [obyekt, L, bekor]
    x = -50.0
    for i in range(R.randint(4, 12)):
        L = R.choice([R.uniform(250, 700), R.uniform(700, 2000), R.uniform(2000, 2800)])
        L = round(L, 1)
        d = [x, L]; l.detal.append(d); detallar.append([d, L, False])
        x -= L + R.uniform(150, 1500)
    toxtash_kerak = 0
    toxtash_soni = R.randint(2, 5)
    oxir = max(1, int((-x + D_HAQ + 600) / l.v_mm_s() * 1000))
    vaqtlar = sorted(R.uniform(0.05, 0.95) * oxir for _ in range(toxtash_soni))
    otgan = 0.0
    for tv in vaqtlar:
        # Stanok ikki to'xtash orasida kamida 1 s ishlasin: 200 ms dan qisqa yonish
        # Pico uchun (to'g'ri ravishda) bitta uzun to'xtash — haqiqatni sanashni buzadi.
        tv = max(tv, otgan + 1000)
        l.yur(max(0, tv - otgan)); otgan = tv
        # chegara yonida bo'lsa — biroz kutamiz (1 mm aniqlikdagi noaniqlikdan qochish)
        for _ in range(400):
            if all(min(abs(f), abs(f - D_HAQ), abs(f - L0), abs(f - L0 - D_HAQ)) > 25 for f, L0 in l.detal):
                break
            l.yur(5); otgan += 5
        ta = False
        for rec in detallar:
            f, L0 = rec[0]
            if rec[0] in l.detal and f > 0 and f - L0 <= D_HAQ:
                rec[2] = True; ta = True
        toxtash_kerak += ta
        run0, v180 = l.run, l.v18
        l.run = False; l.v18 = False; l.pin_run()
        dam = R.uniform(500, 20000); l.yur(dam)
        BUYRUQ.append('STOP')
        l.run, l.v18 = run0, v180; l.pin_run()
    l.yur(oxir - otgan + 60000)
    kutilgan = [rec[1] for rec in detallar if not rec[2]]
    o = olchovlar()
    olch = [e['L'] for e in o]
    ok = (len(olch) == len(kutilgan)
          and all(abs(a - b) < 2.0 for a, b in zip(olch, kutilgan))
          and all(e['kod'] == 'OK' for e in o)
          and not ogohlar()
          and len(toxtashlar()) == toxtash_kerak)
    return ok, {'kutilgan': kutilgan, 'olchandi': olch, 'kodlar': [e['kod'] for e in o],
                'toxtash': (len(toxtashlar()), toxtash_kerak), 'ogoh': ogohlar(),
                'bekor': sum(r[2] for r in detallar), 'jami': len(detallar)}

def S33():
    # TIQILISH: detal D1 dan o'tib, oraliqda uzoq turib qoldi (stanok yonib turibdi).
    # Eski mantiqda navbat muddati tugab yozuv tashlanardi va keyingi o'lchovlar
    # siljib ketardi. Endi navbat kutadi, detal kelganda to'g'ri juftlanadi.
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(500); yetib_bor(l, 700)          # D1 dan butunlay o'tdi
    l.tiq = True; l.yur(60000)             # 60 s tiqilib turdi (eski muddat ~23 s)
    l.tiq = False; l.yur(40000)
    o = olchovlar()
    tekshir('33 tiqilish: oraliqda 60 s turgan detal keyin to\'g\'ri o\'lchandi',
            len(o) == 1 and o[0]['kod'] == 'OK' and abs(o[0]['L'] - 500) < 15, CHIQ)

def S34():
    # TIQILISH: ikki detal bir-biriga tiqilib, D2 dan BIRGA o'tdi.
    # Soxta o'lcham chiqmasligi kerak — "tiqilish" hodisasi va avariya.
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(500); yetib_bor(l, 900)
    l.qoy(600)
    while l.detal[-1][0] < 900:            # ikkinchisi ham D1 dan butunlay o'tsin
        l.yur(5)
    l.detal[1][0] = l.detal[0][0] - l.detal[0][1]   # ikkinchisi birinchisiga tiqildi
    l.yur(40000)
    tq = [e for e in CHIQ if e['ev'] == 'tiqilish']
    tekshir('34 tiqilish: ikki detal birga o\'tdi — soxta o\'lcham yo\'q',
            not olchovlar() and len(tq) == 1 and tq[0]['n'] == 2 and avariya_yoniq(), CHIQ)

def S35():
    # Birinchi detal yo'ldan olib qo'yildi. Ikkinchisi O'ZINING yozuvi bilan
    # juftlanishi kerak. Yo'qolgani jimgina tashlanmaydi: "d2_tasdiqlamadi"
    # hodisasi chiqadi (v1.17 — soxta uzunlik o'rniga rost xabar).
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.qoy(400); yetib_bor(l, 600)
    l.qoy(1200); yetib_bor(l, 1400)
    l.detal.pop(0)                          # birinchisi olib qo'yildi
    l.yur(40000)
    o = olchovlar(); tq = [e for e in CHIQ if e['ev'] == 'tiqilish']
    tekshir('35 yo\'qolgan detal keyingisining o\'lchoviga qo\'shilib ketmaydi',
            len(tq) == 1 and tq[0]['sabab'] == 'd2_tasdiqlamadi' and abs(tq[0]['L1'][0] - 400) < 15
            and len(o) == 1 and o[0]['kod'] == 'OK' and abs(o[0]['L'] - 1200) < 20, CHIQ)

def S36():
    # D2 butunlay ko'rmasa, navbat sig'imgacha to'ladi va shundan keyingina
    # eng eskisi FAQAT1 bo'lib chiqadi — ya'ni ma'lumot yo'qolmaydi, kechikadi.
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.d2_kor = False
    sigim = M.kutuv_sigimi()
    for _ in range(sigim + 2):
        l.qoy(500); l.yur(4000)
    l.yur(20000)
    o = olchovlar()
    tekshir('36 D2 o\'lgan bo\'lsa navbat to\'lgach FAQAT1 chiqa boshlaydi',
            len(o) >= 1 and all(e['kod'] == 'FAQAT1' for e in o) and len(M.kutuv) <= sigim,
            [len(o), [e['kod'] for e in o], len(M.kutuv), sigim])

def S37():
    # 2026-09-21 talabi: D1 dan o'tgan detalni D2 TASDIQLAMASDAN turib, 2-6 s
    # ichida D1 ga yangi detal kiradi. Har bir yozuv o'z detali bilan
    # juftlanishi, ustiga yangisi tushmasligi va navbatdan uchib ketmasligi kerak.
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    uzunlik = [400, 1200, 650, 300]
    for L in uzunlik:
        l.qoy(L)
        yetib_bor_oxirgi(l, L + 120)        # D1 dan butunlay o'tsin
        l.yur(3000)                          # keyingisi 3 s dan keyin kiradi
    l.yur(60000)
    o = olchovlar()
    olchangan = [round(e['L']) for e in o]
    tekshir('37 ketma-ket 4 detal: har biri O\'Z o\'lchovi bilan, tartibda chiqadi',
            len(o) == 4 and all(e['kod'] == 'OK' for e in o)
            and all(abs(olchangan[i] - uzunlik[i]) < 15 for i in range(4)),
            [olchangan, [e['kod'] for e in o]])

def S38():
    # Pico qayta yuklandi (yoki tok uzildi) — yo'lda qolgan detallar D1 yozuvisiz
    # D2 ga keladi. Navbat siljib qolmasligi kerak: yo'ldagi detal FAQAT2 bo'ladi,
    # keyingilari esa O'Z yozuvi bilan, to'g'ri tezlikda o'lchanadi.
    # (Detallar bir xil uzunlikda — uzunlik tekshiruvi bilan ajratib bo'lmaydi,
    #  faqat imkonsiz qisqa dt ko'rsatib beradi.)
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    l.detal.append([1500.0, 447.0])         # D1 dan o'tib bo'lgan, yozuvi yo'q
    l.yur(2000)
    for _ in range(2):                       # keyin oddiy detallar keladi
        l.qoy(447); yetib_bor_oxirgi(l, 600); l.yur(2000)
    l.yur(60000)
    o = olchovlar()
    kod = [e['kod'] for e in o]
    tez = [e for e in ogohlar() if e['sabab'] == 'tezlik_nomuvofiq']
    tekshir('38 qayta yuklashdan keyin yo\'ldagi detal navbatni siljitmaydi',
            len(o) == 3 and kod[0] == 'FAQAT2' and kod[1] == 'OK' and kod[2] == 'OK'
            and not tez and all(abs(e['L'] - 447) < 15 for e in o),
            [kod, [round(e['L'], 1) for e in o], len(tez)])

def S39():
    # 2026-09-21 shikoyati: eng kichik detal 150 mm. Ular ketma-ket, kichik
    # oraliq bilan kelsa, D1 va D2 orasida (2553 mm) bir vaqtda 14-17 tasi
    # bo'ladi. Navbat sig'imi 12 ta bo'lganda eng eski yozuv D2 tasdiqlamasdan
    # chiqib ketardi va navbat siljirdi (uzun detallarda bu hech qachon
    # bo'lmasdi — shuning uchun muammo faqat kalta detallarda ko'rinardi).
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    N = 16
    for i in range(N):                       # 150 mm detal + 40 mm oraliq
        l.qoy(150.0, old=-50.0 - i * 190.0)
    l.yur(120000)
    o = olchovlar()
    tekshir('39 150 mm detallar ketma-ket: hammasi to\'g\'ri, navbat siljimaydi',
            len(o) == N and all(e['kod'] == 'OK' for e in o)
            and all(abs(e['L'] - 150) < 10 for e in o)
            and not [e for e in CHIQ if e['ev'] == 'tiqilish'],
            [len(o), [e['kod'] for e in o][:6], [round(e['L'], 1) for e in o][:6]])

def S40():
    # Turli uzunlikdagi detallar aralash kelganda juftlash chalkashmasin
    # (650 va 800 mm ilgari "bir xil" deb qabul qilinardi — chegara 25% edi).
    l = yangi_holat(); l.run = True; l.pin_run(); l.yur(300)
    uzunlik = [650, 800, 650, 1860, 150, 1100]
    for L in uzunlik:
        l.qoy(L); yetib_bor_oxirgi(l, L + 150); l.yur(1500)
    l.yur(90000)
    o = olchovlar()
    olch = [round(e['L']) for e in o]
    tekshir('40 aralash uzunliklar (650/800/1860/150/1100) to\'g\'ri juftlanadi',
            len(o) == len(uzunlik) and all(e['kod'] == 'OK' for e in o)
            and all(abs(olch[i] - uzunlik[i]) < 15 for i in range(len(uzunlik))),
            [olch, [e['kod'] for e in o]])

def S41():
    # v1.21: yonish sababi (reset_cause) aniqlanadi; "boot" stansiya yo'q paytda
    # xotiraga tushadi va HB kelganda eski_ms bilan chiqadi; HOLAT da sabab va up bor.
    import io, builtins as B
    machine.PWRON_RESET, machine.WDT_RESET = 1, 3
    sabab = []
    for k in (1, 3, 5):
        machine.reset_cause = lambda k=k: k
        sabab.append(M.yonish_sababi())
    del machine.reset_cause
    sabab.append(M.yonish_sababi())                   # reset_cause yo'q platforma
    yangi_holat(); M.yubor = ASL_YUBOR
    M.yigilgan.clear(); M.XOST.update({'oxir': None, 'yoqolgan': 0})
    chiq = []; asl = B.print
    B.print = lambda *a, **k: chiq.append(' '.join(str(x) for x in a))
    try:
        M.yubor({'ev': 'boot', 'sabab': 'wdt', 'ver': M.VER})
        n_xot = len(M.yigilgan)
        M.poll = type('P', (), {'poll': lambda s, t=0: [1]})()
        M.sys.stdin = io.StringIO('HB\nHOLAT\n')
        ASL_BUYRUQ(); ASL_BUYRUQ()
        js = [json.loads(s) for s in chiq if s.startswith('{')]
    finally:
        B.print = asl; M.yubor = lambda d: CHIQ.append(json.loads(json.dumps(d)))
        M.XOST['oxir'] = None
    boot = [j for j in js if j['ev'] == 'boot']
    hol = [j for j in js if j['ev'] == 'holat']
    tekshir('41 yonish sababi: tok/wdt aniqlanadi, boot xotiradan chiqadi, HOLAT da sabab/up',
            sabab == ['tok', 'wdt', '5', '?'] and n_xot == 1 and boot and boot[0]['sabab'] == 'wdt'
            and 'eski_ms' in boot[0] and hol and 'sabab' in hol[0] and 'up' in hol[0]
            and hol[0]['ver'] == M.VER, [sabab, js])

def yetib_bor_oxirgi(l, x, ms_max=120000):
    """Oxirgi qo'yilgan detal old qirrasi x ga yetguncha yurgizish."""
    for _ in range(ms_max // 5):
        if l.detal and l.detal[-1][0] >= x:
            return
        l.yur(5)
    raise RuntimeError('yetib bormadi')

if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if N:
        yaxshi = 0; detal_j = 0; bekor_j = 0; tox_j = 0
        for s in range(N):
            ok, info = tasodifiy(s)
            yaxshi += ok; detal_j += info['jami']; bekor_j += info['bekor']; tox_j += info['toxtash'][1]
            if not ok:
                print('  XATO seed=%d  %s' % (s, info))
        print('\n  tasodifiy: %d / %d o\'tdi  (detal %d, shundan bekor %d, avariyali to\'xtash %d)'
              % (yaxshi, N, detal_j, bekor_j, tox_j))
        sys.exit(0 if yaxshi == N else 1)
    for f in [v for k, v in sorted(globals().items()) if k.startswith('S') and k[1:].isdigit()]:
        try:
            f()
        except Exception as e:
            import traceback
            tekshir(f.__name__, False, traceback.format_exc())
    yaxshi = 0
    for nom, ok, izoh in NATIJA:
        print(('  OK   ' if ok else '  XATO ') + nom)
        if not ok:
            print('        ', str(izoh)[:1500])
        yaxshi += ok
    print('\n  %d / %d o\'tdi' % (yaxshi, len(NATIJA)))
    sys.exit(0 if yaxshi == len(NATIJA) else 1)
