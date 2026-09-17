# main.py — KROMKA STANSIYASI KONTROLLERI  (TZ v1.2, proshivka v1.9)
#
# OYOQCHALAR — TZ 3-bo'lim, boshqa pin ishlatilmaydi:
#   GP1  (2-pin)   <- datchik 1 optopara 4-oyoq   (kirish)
#   GP5  (7-pin)   <- datchik 2 optopara 4-oyoq   (chiqish)
#   GP9  (12-pin)  <- RUN optopara 4-oyoq          (uskuna ishlayapti = 10 m/min)
#   GP13 (17-pin)  <- 18 m/min optopara 4-oyoq
#   GP0  (1-pin)   -> rele moduli IN               (sakratkich Low, lampa) — YAGONA rele
#   GP16 (21-pin)  -> R2 10k -> A nuqta -> C1 -> usilitel NL
#   GND            <- barcha optoparalar 3-oyoq, rele DC-, usilitel GND, AL-2402 0V
#
# BUYRUQLAR (brauzerdan, har biri \n bilan tugaydi):
#   QR                          lampa + tovush ikki marta (150 bor - 150 jim - 150 bor)
#   ALARM                       avariya rejimi: lampa + sirena 1 s yonadi / 1 s o'chadi
#   STOP                        avariyani to'xtatish
#   TEST                        lampa + sirena 1 s
#   KALIB 1  /  KALIB 0         kalibrlash rejimi
#   SET D=.. V10=.. V18=.. K1=.. K2=.. C=.. TD=.. AO=0|1
#   PING                        tiriklik tekshiruvi
#   HOLAT                       joriy holat
#
# CHIQISH: har qator JSON. Thonny da o'qish uchun CHOP = True.

from machine import Pin, PWM
import time, sys, select, json

# ================= OYOQCHALAR =================
GP_D1, GP_D2      = 1, 5
GP_RUN, GP_V18    = 9, 13
GP_RELE, GP_AUDIO = 0, 16

# ================= SOZLAMALAR =================
FAOL_PAST   = True     # optopara chiqishi faol bo'lganda kirish PASTGA tushadi
MIN_US      = 50000    # 50 ms dan qisqa signal - shovqin
STUCK_S     = 30       # yopishib qolish chegarasi
XATO_N      = 3        # javob_yoq uchun ketma-ketlik
IFLOS_N     = 5        # iflos uchun ketma-ketlik
TOL_TEZLIK  = 20.0     # tezlik nomuvofiqligi, %
XOTIRA_N    = 10
CHOP        = True     # Thonny uchun o'qiladigan matn

# Kalibrlash — SET buyrug'i bilan brauzerdan keladi
#   D      datchiklar orasidagi effektiv masofa, mm
#   K1/K2  har datchikning O'Z kechikish tuzatmasi, ms:  t = L/v + k
#   C      markazlar orasidagi o'tish vaqtiga tuzatma, ms:  dt_mid = D/v + C
#   V10/V18  zaxira tezlik — faqat dt o'lchanmaganda ishlatiladi
#   TD     datchiklar farqi chegarasi, mm
#   AO     avariya signali O'CHIRILGAN (1 = lampa/sirena chalinmaydi)
#          Hodisalar baribir yuboriladi va MES ga yoziladi — faqat
#          ko'rinadigan/eshitiladigan ogohlantirish bosiladi. Sozlash va
#          o'lchov sinovi paytida shovqin qilmasligi uchun.
KAL = {'D': 2555.0, 'V10': 10.0, 'V18': 18.0,
       'K1': 0.0, 'K2': 0.0, 'C': 0.0, 'TD': 12.0, 'AO': 0.0}

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

# Oxirgi holat eslab qolinadi: har 5 ms da PWM chastotasini qayta yozish
# tovushni g'ijirlatadi, releni esa keraksiz qo'zg'atadi.
_oxir = {'lampa': None, 'hz': None}

def lampa(on):
    on = True if on else False
    if _oxir['lampa'] is not on:
        _oxir['lampa'] = on
        rele.value(0 if on else 1)

def tovush(hz):
    hz = int(hz) if hz else 0
    if _oxir['hz'] == hz:
        return
    _oxir['hz'] = hz
    if hz:
        buz.freq(hz); buz.duty_u16(32768)
    else:
        buz.duty_u16(0)

def yubor(d):
    print(json.dumps(d))

def chop(s):
    if CHOP:
        print(s)

# ================= DATCHIKLAR =================
#
# HAR DATCHIK BUTUNLAY MUSTAQIL ISHLAYDI.
#
# Nega: datchiklar orasi D = ~2556 mm. 300 mm detal 150 mm oraliq bilan
# kelsa, D1 dan D2 gacha bo'lgan yo'lda BIR VAQTNING O'ZIDA 5-6 ta detal
# bo'ladi. Ilgari D1 va D2 uchun bittadan joy bor edi — D1 keyingi detalni
# ko'rganda oldingisining ma'lumoti hali D2 dan kelmagan bo'lardi va ustma-ust
# tushib, o'lchovni buzardi.
#
# Yechim: D1 tugatgan har bir detal NAVBATGA qo'yiladi. D2 detalni tugatganda
# navbatdan eng eskisini oladi va shu bilan juftlaydi. Lenta transporter —
# detallar bir-birini quvib o'tolmaydi, shuning uchun D2 dagi tartib D1 dagi
# tartib bilan aynan bir xil. Har datchik nur ochilishi bilan DARHOL keyingi
# detalga tayyor: kutish yo'q.
navbat = []
kuzat = {1: {'us': None, 'ms': None, 'yopiq': False, 'stuck': False},
         2: {'us': None, 'ms': None, 'yopiq': False, 'stuck': False}}

# D1 dan o'tib bo'lgan, D2 ni kutayotgan detallar navbati (FIFO).
kutuv = []
KUTUV_MAX = 12       # oraliqqa sig'adigan detaldan ko'p bo'lsa — nimadir noto'g'ri

def qur(kanal, gpio):
    p = Pin(gpio, Pin.IN, Pin.PULL_UP)
    def chekka(pin):
        # vaqt eng birinchi o'qiladi — sathni talqin qilish asosiy siklga qoladi
        t = time.ticks_us()
        navbat.append((kanal, pin.value(), t, time.ticks_ms()))
    p.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=chekka)
    return p

p_d1 = qur(1, GP_D1)
p_d2 = qur(2, GP_D2)

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

def d2_kutish_ms(S=None):
    """Detal D1 dan D2 gacha yetib borishi uchun beriladigan eng uzoq vaqt.

    Navbatdagi yozuv shundan uzoq turib qolsa — D2 uni ko'rmagan, ya'ni
    datchik javob bermadi. Nominal o'tish vaqti D/v, ustiga 50% zaxira.
    """
    if S is None:
        S = S_detal
    v = KAL['V18'] if S == 18 else KAL['V10']
    if v <= 0 or KAL['D'] <= 0:
        return 20000
    return int(KAL['D'] / (v * 1000.0 / 60.0) * 1500.0) + 500

# ================= OGOHLANTIRISH REJIMLARI =================
AL = {'rejim': 'IDLE', 't0': 0}

def avariya_boshla():
    # AO=1 bo'lsa lampa va sirena chalinmaydi. Hodisa (ogoh/olchov) baribir
    # yuboriladi — sozlash paytida muammoni ko'rish uchun, lekin shovqinsiz.
    if KAL['AO']:
        return
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
        # TZ 7.1: ikki qisqa signal — 150 ms lampa+tovush, 150 ms pauza,
        # 150 ms lampa+tovush. Rele ikki marta tortib, ikki marta qo'yib yuboradi.
        if e < 450:
            yon = e < 150 or e >= 300
            lampa(yon); tovush(1000 if yon else 0)
        else:
            AL['rejim'] = 'IDLE'; lampa(False); tovush(0)
    elif r == 'TEST':
        if e < 1000:
            lampa(True); tovush(1000)
        else:
            AL['rejim'] = 'IDLE'; lampa(False); tovush(0)
    elif r == 'AVARIYA':
        # TZ 7.2: lampa va sirena qat'iy BIRGA — 1 s ikkalasi yonadi, 1 s ikkalasi
        # o'chadi. Yongan paytda ohang 800 va 1200 Hz orasida almashadi.
        yon = (e // 1000) % 2 == 0
        lampa(yon)
        tovush((800 if (e // 250) % 2 == 0 else 1200) if yon else 0)

def ogoh(ch, sabab, q=0.0):
    yubor({'ev': 'ogoh', 'ch': ch, 'sabab': sabab, 'q': round(q, 2)})
    chop("  !! OGOH: datchik %d — %s" % (ch, sabab))
    avariya_boshla()

# ================= NAVBAT: D1 -> D2 JUFTLASH =================
def d1_tugadi(us, ms, dur):
    """D1 detalni butunlay o'tkazdi — navbatga qo'yamiz, D2 ni kutadi."""
    kutuv.append({'us': us, 'ms': ms, 'dur': dur, 'S': tezlik_nom()})
    chop("  > D1 o'tkazdi (%.0f ms), navbatda %d ta" % (dur / 1000.0, len(kutuv)))
    if len(kutuv) > KUTUV_MAX:
        # Oraliqqa sig'adiganidan ko'p to'planib qoldi — eng eskisi yo'qolgan.
        r = kutuv.pop(0)
        yakunla(r, None, None)

def d2_tugadi(us, dur):
    """D2 detalni o'tkazdi — navbatdagi ENG ESKI yozuv bilan juftlaymiz."""
    if kutuv:
        yakunla(kutuv.pop(0), dur, us)
    else:
        yakunla(None, dur, us)          # D1 bu detalni ko'rmagan

def kutuvni_tekshir(hozir_ms):
    """Navbat boshidagi yozuv juda uzoq kutdimi — D2 uni ko'rmagan."""
    while kutuv:
        r = kutuv[0]
        if time.ticks_diff(hozir_ms, r['ms']) > d2_kutish_ms(r['S']):
            kutuv.pop(0)
            yakunla(r, None, None)
        else:
            break                        # navbat vaqt bo'yicha tartiblangan

# ================= DETALNI YAKUNLASH =================
def yakunla(r1, d2, us2):
    """Bitta detalni yakunlaydi.

    r1  — D1 yozuvi {'us','ms','dur','S'} yoki None (D1 ko'rmagan)
    d2  — D2 nurni to'sib turgan vaqt, µs yoki None (D2 ko'rmagan)
    us2 — D2 old qirrani tutgan lahza, µs yoki None
    """
    global son
    d1 = r1['dur'] if r1 else None
    S = r1['S'] if r1 else S_detal

    # old frontlar orasidagi vaqt
    dt = None
    if r1 is not None and us2 is not None:
        dt = time.ticks_diff(us2, r1['us'])
        if dt <= 0:
            dt = None

    # MARKAZLAR bo'yicha vaqt: detal o'rtasi D1 dan D2 gacha qancha yurdi.
    #   dt_mid = dt + (d2 - d1) / 2
    # Old va orqa frontlarning kechikishi o'zaro qisqaradi, tezlik esa aynan
    # detal o'tgan oraliqda o'lchanadi — shuning uchun bu aniqroq.
    dtm = dt
    if dt is not None and d1 and d2:
        dtm = dt + (d2 - d1) / 2.0

    v_eff_S = KAL['V18'] if S == 18 else KAL['V10']
    yangi = 0
    v_olch = None
    dtc = (dtm - KAL['C'] * 1000.0) if dtm is not None else None
    if dtc and dtc > 0 and KAL['D'] > 0:
        v_mm_us = KAL['D'] / dtc
        v_olch = v_mm_us * 60000.0
        yangi = 1
        xotira.append(v_olch)
        if len(xotira) > XOTIRA_N:
            xotira.pop(0)
        if v_eff_S > 0 and abs(v_olch - v_eff_S) / v_eff_S * 100.0 > TOL_TEZLIK:
            ogoh(0, 'tezlik_nomuvofiq', v_olch)
    else:
        v_mm_us = v_eff_S / 60000.0

    L1 = v_mm_us * (d1 - KAL['K1'] * 1000.0) if d1 else None
    L2 = v_mm_us * (d2 - KAL['K2'] * 1000.0) if d2 else None

    shubha = 0
    farq = 0.0
    if L1 is not None and L2 is not None:
        farq = abs(L1 - L2)
        if farq <= KAL['TD']:
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
        return

    son += 1
    rec = {'ev': 'olchov', 'n': son, 'L': round(L, 1), 'kod': kod, 'shubha': shubha,
           'L1': round(L1, 1) if L1 is not None else None,
           'L2': round(L2, 1) if L2 is not None else None,
           'd1': d1 or 0, 'd2': d2 or 0,
           'v_olch': round(v_olch, 2) if v_olch else None,
           'v_nom': S, 'yangi': yangi,
           'ish_ms': round(dt / 1000.0, 1) if dt else None,
           'farq': round(farq, 1), 'navbat': len(kutuv)}
    yubor(rec)

    if kalib_rejim:
        yubor({'ev': 'kalib', 'S': S, 't1': d1 or 0, 't2': d2 or 0,
               'dt': dt or 0, 'dtm': int(dtm) if dtm else 0})

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
            print("  D1->D2    : %.0f ms" % (dt / 1000.0))
        print("  Navbatda  : %d ta detal" % len(kutuv))
        print("  NATIJA    : %.1f mm" % L)
        print("  ------------------------------------------")
        print("")

# ================= BUYRUQLAR =================
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

def buyruq_tekshir():
    global kalib_rejim
    if not poll.poll(0):
        return
    line = sys.stdin.readline()
    if not line:
        return
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
                try:
                    f = float(v)
                except ValueError:
                    continue
                if k == 'K':                     # eski format — ikkalasiga bir xil
                    KAL['K1'] = KAL['K2'] = f
                elif k in KAL:
                    KAL[k] = f
        # AO yoqilgan bo'lsa va shu payt avariya chalinayotgan bo'lsa — o'chiramiz
        if KAL['AO'] and AL['rejim'] == 'AVARIYA':
            avariya_toxtat()
        yubor({'ev': 'kal', 'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18'],
               'K1': KAL['K1'], 'K2': KAL['K2'], 'C': KAL['C'], 'TD': KAL['TD'],
               'AO': KAL['AO']})
        chop("  kalibrlash saqlandi: D=%.2f V10=%.3f V18=%.3f K1=%.3f K2=%.3f C=%.3f TD=%.1f"
             % (KAL['D'], KAL['V10'], KAL['V18'], KAL['K1'], KAL['K2'], KAL['C'], KAL['TD']))
        chop("  avariya signali: %s" % ("O'CHIQ" if KAL['AO'] else 'yoniq'))
    elif cmd == 'PING':
        yubor({'ev': 'pong', 'up': time.ticks_ms()})
    elif cmd == 'HOLAT':
        yubor({'ev': 'holat', 'alarm': 1 if AL['rejim'] == 'AVARIYA' else 0,
               'uskuna': uskuna_holat(), 'v_nom': tezlik_nom(),
               'kalib': 1 if kalib_rejim else 0, 'n': son, 'navbat': len(kutuv),
               'ver': '1.9',
               'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18'],
               'K1': KAL['K1'], 'K2': KAL['K2'], 'C': KAL['C'], 'TD': KAL['TD'],
               'AO': KAL['AO']})

# ================= BOSHLANISH =================
yubor({'ev': 'boot', 'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18']})
if CHOP:
    print("=" * 50)
    print("  KROMKA STANSIYASI KONTROLLERI  v1.9")
    print("  D1=GP%d  D2=GP%d  RUN=GP%d  V18=GP%d  RELE=GP%d  AUDIO=GP%d"
          % (GP_D1, GP_D2, GP_RUN, GP_V18, GP_RELE, GP_AUDIO))
    print("  Buyruqlar: QR ALARM STOP TEST KALIB SET PING HOLAT")
    print("=" * 50)

usk_old = -1
v_old = -1

# ================= ASOSIY SIKL =================
while True:
    buyruq_tekshir()

    # HAR DATCHIK MUSTAQIL: nur to'silganda vaqt olinadi, ochilganda detal
    # tugagan deb hisoblanadi va DARHOL keyingisiga tayyor bo'ladi.
    while navbat:
        kanal, sath, t, m = navbat.pop(0)
        e = (sath == 0) if FAOL_PAST else (sath == 1)
        s = kuzat[kanal]
        if e:
            if s['yopiq']:
                continue
            s['yopiq'] = True
            s['stuck'] = False
            s['us'] = t
            s['ms'] = m
            if kanal == 1:
                S_detal = tezlik_nom()
        else:
            if not s['yopiq']:
                continue
            s['yopiq'] = False
            if s['us'] is None:
                continue
            d = time.ticks_diff(t, s['us'])
            s['us'] = None
            if d < MIN_US:
                continue                      # shovqin — hisobga olinmaydi
            if kanal == 1:
                d1_tugadi(time.ticks_add(t, -d), s['ms'], d)
            else:
                d2_tugadi(time.ticks_add(t, -d), d)

    hozir = time.ticks_ms()

    for k in (1, 2):
        s = kuzat[k]
        if s['yopiq'] and not s['stuck'] and s['ms'] is not None:
            if time.ticks_diff(hozir, s['ms']) > STUCK_S * 1000:
                s['stuck'] = True
                s['yopiq'] = False
                s['us'] = None
                ogoh(k, 'yopishib_qolgan')

    # D2 ga yetib bormagan detallar bormi
    kutuvni_tekshir(hozir)

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

    alarm_tick()
    led.value(1 if (kuzat[1]['yopiq'] or kuzat[2]['yopiq']) else 0)
    time.sleep_ms(5)
