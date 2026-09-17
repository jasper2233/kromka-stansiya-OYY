# main.py — KROMKA STANSIYASI KONTROLLERI  (TZ v1.2)
#
# OYOQCHALAR — siz ulagan holat:
#   GP1  (2-pin)   <- datchik 1 optopara 4-oyoq   (kirish)
#   GP5  (7-pin)   <- datchik 2 optopara 4-oyoq   (chiqish)
#   GP9  (12-pin)  <- RUN optopara 4-oyoq          (uskuna ishlayapti = 10 m/min)
#   GP13 (17-pin)  <- 18 m/min optopara 4-oyoq
#   GP0  (1-pin)   -> rele moduli IN               (sakratkich Low)
#   GP16 (21-pin)  -> R2 10k -> A nuqta -> C1 -> usilitel NL
#   GND            <- barcha optoparalar 3-oyoq, rele DC-, usilitel GND, AL-2402 0V
#
# BUYRUQLAR (brauzerdan, har biri \n bilan tugaydi):
#   QR                          ikki qisqa signal
#   ALARM                       avariya rejimi
#   STOP                        avariyani to'xtatish
#   TEST                        lampa + sirena 1 s
#   KALIB 1  /  KALIB 0         kalibrlash rejimi
#   SET D=2003.4 V10=9.87 V18=17.92 K=1.2
#   HOLAT                       joriy holat + uskuna/tezlikni qayta yuborish
#   PING                        aloqani tekshirish (pong qaytadi)
#
# CHIQISH: har qator JSON. Thonny da o'qish uchun CHOP = True.
# Har TIK_MS da {"ev":"tik",...} yuboriladi - brauzer shundan aloqa
# tirikligini biladi (ilgari datchik tegmaguncha umuman jim turardi).

from machine import Pin, PWM
from array import array
import time, sys, select, json

# ================= OYOQCHALAR =================
GP_D1, GP_D2      = 1, 5
GP_RUN, GP_V18    = 9, 13
GP_RELE, GP_AUDIO = 0, 16

# ================= SOZLAMALAR =================
FAOL_PAST   = True     # optopara chiqishi faol bo'lganda kirish PASTGA tushadi
MIN_US      = 50000    # 50 ms dan qisqa signal - shovqin
SETTLE_MS   = 300      # detal tugadi deb hisoblash uchun tinchlik
STUCK_S     = 30       # yopishib qolish chegarasi
XATO_N      = 3        # javob_yoq uchun ketma-ketlik
IFLOS_N     = 5        # iflos uchun ketma-ketlik
TOL_DATCHIK = 3.0      # ikki datchik farqi chegarasi, mm
TOL_TEZLIK  = 20.0     # tezlik nomuvofiqligi, %
XOTIRA_N    = 10
CHOP        = True     # Thonny uchun o'qiladigan matn
TIK_MS      = 1000     # har soniyada "tirikman" paketi - brauzer aloqani shundan ko'radi

# Kalibrlash — SET buyrug'i bilan brauzerdan keladi
KAL = {'D': 2000.0, 'V10': 10.0, 'V18': 18.0, 'K': 0.0}

# ================= APPARAT =================
def yopiq(p):
    return (p.value() == 0) if FAOL_PAST else (p.value() == 1)

p_run = Pin(GP_RUN, Pin.IN, Pin.PULL_UP)
p_v18 = Pin(GP_V18, Pin.IN, Pin.PULL_UP)
rele  = Pin(GP_RELE, Pin.OUT, value=1)        # 1 = o'chiq (Low trigger)
buz   = PWM(Pin(GP_AUDIO))
buz.duty_u16(0)
try:
    led = Pin("LED", Pin.OUT)
except (TypeError, ValueError):
    led = Pin(25, Pin.OUT)

def lampa(on):
    rele.value(0 if on else 1)

def tovush(hz):
    if hz:
        buz.freq(int(hz)); buz.duty_u16(32768)
    else:
        buz.duty_u16(0)

def yubor(d):
    print(json.dumps(d))

def chop(s):
    if CHOP:
        print(s)

# ================= DATCHIKLAR =================
# IRQ ichida ro'yxatga append qilish xotira ajratadi -> "MemoryError: heap is locked"
# va kontroller jim qolib ketadi. Shuning uchun oldindan ajratilgan halqa bufer.
NAVBAT_N = 64
q_kan = bytearray(NAVBAT_N)
q_lvl = bytearray(NAVBAT_N)
q_us  = array('i', [0] * NAVBAT_N)
q_ms  = array('i', [0] * NAVBAT_N)
q_w   = 0
q_r   = 0

st = {1: {'us': None, 'ms': None, 'dur': None, 'yopiq': False, 'stuck': False},
      2: {'us': None, 'ms': None, 'dur': None, 'yopiq': False, 'stuck': False}}

def qur(kanal, gpio):
    p = Pin(gpio, Pin.IN, Pin.PULL_UP)
    def chekka(pin):
        global q_w
        i = q_w
        q_kan[i] = kanal
        q_lvl[i] = 1 if yopiq(pin) else 0
        q_us[i]  = time.ticks_us()
        q_ms[i]  = time.ticks_ms()
        q_w = (i + 1) % NAVBAT_N
    p.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=chekka)
    return p

p_d1 = qur(1, GP_D1)
p_d2 = qur(2, GP_D2)

faol = False
oxirgi_ms = 0
S_detal = 10
xotira = []
xato  = {1: 0, 2: 0}
iflos = {1: 0, 2: 0}
son = 0
kalib_rejim = False

def tezlik_nom():
    return 18 if yopiq(p_v18) else 10

def uskuna_holat():
    return 1 if (yopiq(p_run) or yopiq(p_v18)) else 0

# ================= OGOHLANTIRISH REJIMLARI =================
AL = {'rejim': 'IDLE', 't0': 0}

def avariya_boshla():
    if AL['rejim'] != 'AVARIYA':
        AL['rejim'] = 'AVARIYA'
        AL['t0'] = time.ticks_ms()
        yubor({'ev': 'holat', 'alarm': 1})
        chop("  !! AVARIYA — STOP buyrug'igacha davom etadi")

def avariya_toxtat():
    AL['rejim'] = 'IDLE'
    lampa(False); tovush(0)
    yubor({'ev': 'holat', 'alarm': 0})
    chop("  avariya to'xtatildi")

def qr_boshla():
    if AL['rejim'] == 'AVARIYA':
        return
    AL['rejim'] = 'QR'; AL['t0'] = time.ticks_ms()

def test_boshla():
    if AL['rejim'] == 'AVARIYA':
        return
    AL['rejim'] = 'TEST'; AL['t0'] = time.ticks_ms()

def alarm_tick():
    r = AL['rejim']
    if r == 'IDLE':
        return
    e = time.ticks_diff(time.ticks_ms(), AL['t0'])
    if r == 'QR':
        if e < 150 or 300 <= e < 450:
            lampa(True); tovush(1000)
        elif e >= 450:
            AL['rejim'] = 'IDLE'; lampa(False); tovush(0)
        else:
            lampa(False); tovush(0)
    elif r == 'TEST':
        if e < 1000:
            lampa(True); tovush(1000)
        else:
            AL['rejim'] = 'IDLE'; lampa(False); tovush(0)
    elif r == 'AVARIYA':
        if (e // 1000) % 2 == 0:
            lampa(True)
            tovush(800 if (e // 250) % 2 == 0 else 1200)
        else:
            lampa(False); tovush(0)

def ogoh(ch, sabab, q=0.0):
    yubor({'ev': 'ogoh', 'ch': ch, 'sabab': sabab, 'q': round(q, 2)})
    chop("  !! OGOH: datchik %d — %s" % (ch, sabab))
    avariya_boshla()

# ================= DETALNI YAKUNLASH =================
def detalni_yop():
    global faol, son
    d1, d2 = st[1]['dur'], st[2]['dur']
    S = S_detal
    k_us = KAL['K'] * 1000.0

    dt = None
    if st[1]['us'] is not None and st[2]['us'] is not None:
        dt = time.ticks_diff(st[2]['us'], st[1]['us'])
        if dt <= 0:
            dt = None

    v_eff_S = KAL['V18'] if S == 18 else KAL['V10']
    yangi = 0
    v_olch = None
    if dt and KAL['D'] > 0:
        v_mm_us = KAL['D'] / dt
        v_olch = v_mm_us * 60000.0
        yangi = 1
        xotira.append(v_olch)
        if len(xotira) > XOTIRA_N:
            xotira.pop(0)
        if v_eff_S > 0 and abs(v_olch - v_eff_S) / v_eff_S * 100.0 > TOL_TEZLIK:
            ogoh(0, 'tezlik_nomuvofiq', v_olch)
    else:
        v_mm_us = v_eff_S / 60000.0

    L1 = v_mm_us * (d1 - k_us) if d1 else None
    L2 = v_mm_us * (d2 - k_us) if d2 else None

    shubha = 0
    farq = 0.0
    if L1 is not None and L2 is not None:
        farq = abs(L1 - L2)
        if farq <= TOL_DATCHIK:
            L = (L1 + L2) / 2.0; kod = "OK"
            iflos[1] = iflos[2] = 0
        else:
            L = min(L1, L2); kod = "FARQ"
            shubha = 1 if L1 > L2 else 2
            iflos[shubha] += 1
            iflos[3 - shubha] = 0
            if iflos[shubha] >= IFLOS_N:
                ogoh(shubha, 'iflos', farq)
                iflos[shubha] = 0
            else:
                avariya_boshla()
        xato[1] = xato[2] = 0
    elif L1 is not None:
        L, kod, shubha = L1, "FAQAT1", 2
        xato[2] += 1; xato[1] = 0
        if xato[2] == XATO_N:
            ogoh(2, 'javob_yoq')
        else:
            avariya_boshla()
    elif L2 is not None:
        L, kod, shubha = L2, "FAQAT2", 1
        xato[1] += 1; xato[2] = 0
        if xato[1] == XATO_N:
            ogoh(1, 'javob_yoq')
        else:
            avariya_boshla()
    else:
        _reset(); return

    son += 1
    rec = {'ev': 'olchov', 'n': son, 'L': round(L, 1), 'kod': kod, 'shubha': shubha,
           'L1': round(L1, 1) if L1 is not None else None,
           'L2': round(L2, 1) if L2 is not None else None,
           'd1': d1 or 0, 'd2': d2 or 0,
           'v_olch': round(v_olch, 2) if v_olch else None,
           'v_nom': S, 'yangi': yangi,
           'ish_ms': round(dt / 1000.0, 1) if dt else None,
           'farq': round(farq, 1)}
    yubor(rec)

    if kalib_rejim:
        yubor({'ev': 'kalib', 'S': S, 't1': d1 or 0, 't2': d2 or 0, 'dt': dt or 0})

    if CHOP:
        print("")
        print("  ------- O'LCHOV #%d  [%s]  %d m/min -------" % (son, kod, S))
        if v_olch:
            print("  Tezlik    : %.2f m/min (o'lchandi)" % v_olch)
        else:
            print("  Tezlik    : %.2f m/min (zaxira)" % v_eff_S)
        print("  Datchik 1 : %s" % ("%.1f mm" % L1 if L1 is not None else "javob yo'q"))
        print("  Datchik 2 : %s" % ("%.1f mm" % L2 if L2 is not None else "javob yo'q"))
        if shubha:
            print("  Shubhali  : DATCHIK %d  (farq %.1f mm)" % (shubha, farq))
        if dt:
            print("  Ishlov    : %.0f ms" % (dt / 1000.0))
        print("  NATIJA    : %.1f mm" % L)
        print("  ------------------------------------------")
        print("")
    _reset()

def _reset():
    global faol
    faol = False
    for k in (1, 2):
        st[k].update({'us': None, 'ms': None, 'dur': None})

# ================= BUYRUQLAR =================
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
kirish = ''

def buyruq_tekshir():
    # Bloklanmaydigan o'qish. Eski kod sys.stdin.readline() ishlatardi:
    # yarim qator kelib qolsa u qator oxirini kutib turib butun asosiy
    # siklni muzlatib qo'yardi - kontroller butunlay jim bo'lib qolardi.
    global kirish
    n = 0
    while poll.poll(0):
        c = sys.stdin.read(1)
        if not c:
            break
        if ord(c) == 10 or ord(c) == 13:   # qator tugadi
            line = kirish
            kirish = ''
            if line.strip():
                buyruq_bajar(line)
        else:
            kirish += c
            if len(kirish) > 200:
                kirish = ''
        n += 1
        if n > 400:
            break

def buyruq_bajar(line):
    global kalib_rejim, usk_old, v_old
    q = line.strip().split()
    if not q:
        return
    cmd = q[0].upper()
    if cmd == 'QR':
        qr_boshla()
    elif cmd == 'ALARM':
        avariya_boshla()
    elif cmd == 'STOP':
        avariya_toxtat()
    elif cmd == 'TEST':
        test_boshla()
    elif cmd == 'KALIB':
        kalib_rejim = len(q) > 1 and q[1] == '1'
        yubor({'ev': 'kalib_rejim', 'on': 1 if kalib_rejim else 0})
        chop("  kalibrlash: %s" % ("YOQILDI" if kalib_rejim else "o'chirildi"))
    elif cmd == 'SET':
        for kv in q[1:]:
            if '=' in kv:
                k, v = kv.split('=', 1)
                k = k.upper()
                if k in KAL:
                    try:
                        KAL[k] = float(v)
                    except ValueError:
                        pass
        yubor({'ev': 'kal', 'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18'], 'K': KAL['K']})
        chop("  kalibrlash saqlandi: D=%.1f V10=%.2f V18=%.2f K=%.1f"
             % (KAL['D'], KAL['V10'], KAL['V18'], KAL['K']))
    elif cmd == 'PING':
        yubor({'ev': 'pong', 'up': time.ticks_ms()})
    elif cmd == 'HOLAT':
        yubor({'ev': 'holat', 'alarm': 1 if AL['rejim'] == 'AVARIYA' else 0,
               'uskuna': uskuna_holat(), 'v_nom': tezlik_nom(),
               'kalib': 1 if kalib_rejim else 0, 'n': son,
               'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18'], 'K': KAL['K']})
        # uskuna/tezlik hodisalari faqat o'zgarganda yuboriladi - brauzer kech
        # ulangani uchun ularni ko'rmagan. Majburan qayta yuborilsin.
        usk_old = -1
        v_old = -1

# ================= BOSHLANISH =================
yubor({'ev': 'boot', 'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18']})
if CHOP:
    print("=" * 50)
    print("  KROMKA STANSIYASI KONTROLLERI  v1.2")
    print("  D1=GP%d  D2=GP%d  RUN=GP%d  V18=GP%d  RELE=GP%d  AUDIO=GP%d"
          % (GP_D1, GP_D2, GP_RUN, GP_V18, GP_RELE, GP_AUDIO))
    print("  Buyruqlar: QR ALARM STOP TEST KALIB SET HOLAT PING")
    print("  Har %d ms da {\"ev\":\"tik\"} yuboriladi - aloqa tirikligi belgisi" % TIK_MS)
    print("=" * 50)

usk_old = -1
v_old = -1
tik_t   = time.ticks_ms()

# ================= ASOSIY SIKL =================
while True:
    buyruq_tekshir()

    while q_r != q_w:
        i = q_r
        kanal = q_kan[i]
        e     = q_lvl[i]
        t     = q_us[i]
        m     = q_ms[i]
        q_r = (i + 1) % NAVBAT_N
        s = st[kanal]
        if e:
            if s['yopiq']:
                continue
            s['yopiq'] = True; s['stuck'] = False
            if s['us'] is None:
                s['us'] = t; s['ms'] = m
                if kanal == 1:
                    S_detal = tezlik_nom()
                    chop("  > detal kirdi  (%d m/min)" % S_detal)
            faol = True
        else:
            if not s['yopiq']:
                continue
            s['yopiq'] = False
            if s['us'] is not None and s['dur'] is None:
                d = time.ticks_diff(t, s['us'])
                if d >= MIN_US:
                    s['dur'] = d
        oxirgi_ms = m

    hozir = time.ticks_ms()

    for k in (1, 2):
        s = st[k]
        if s['yopiq'] and not s['stuck'] and s['ms'] is not None:
            if time.ticks_diff(hozir, s['ms']) > STUCK_S * 1000:
                s['stuck'] = True
                s['yopiq'] = False
                s['dur'] = None
                ogoh(k, 'yopishib_qolgan')

    if faol and not st[1]['yopiq'] and not st[2]['yopiq']:
        if time.ticks_diff(hozir, oxirgi_ms) > SETTLE_MS:
            detalni_yop()

    u = uskuna_holat()
    if u != usk_old:
        usk_old = u
        yubor({'ev': 'uskuna', 'holat': u})
        chop("  uskuna: %s" % ("ISHLAYAPTI" if u else "to'xtadi"))
    v = tezlik_nom()
    if v != v_old:
        v_old = v
        yubor({'ev': 'tezlik', 'v': v})
        chop("  tezlik: %d m/min" % v)

    if time.ticks_diff(hozir, tik_t) >= TIK_MS:
        tik_t = hozir
        yubor({'ev': 'tik', 'uskuna': u, 'v_nom': v, 'n': son,
               'alarm': 1 if AL['rejim'] == 'AVARIYA' else 0,
               'kalib': 1 if kalib_rejim else 0})

    alarm_tick()
    led.value(1 if (st[1]['yopiq'] or st[2]['yopiq']) else 0)
    time.sleep_ms(5)
