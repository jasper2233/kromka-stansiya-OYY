# main.py — IKKI DATCHIKLI REZERVLANGAN O'LCHOV
#
# Har bir datchik uzunlikni mustaqil o'lchaydi. Natijalar solishtiriladi.
# Bitta datchik ifloslansa yoki ishlamay qolsa, tizim to'xtamaydi —
# ikkinchisi bilan ishlashda davom etadi va nosozlikni xabar qiladi.
#
# ULANISH
#   GP2 (4-pin)  <- 1-optopara 4-oyoq   (kirish datchigi)
#   GP6 (9-pin)  <- 2-optopara 4-oyoq   (chiqish datchigi)
#   GND (3-pin)  <- ikkala optoparaning 3-oyog'i
#
# CHIQISH: har bir qator JSON. Brauzer faqat "{" bilan boshlanganini o'qiydi,
# shuning uchun CHOP = True bo'lganda o'qiladigan matn ham chiqaverishi mumkin.

from machine import Pin
import time

# ===================== SOZLAMALAR =====================
GP_S1      = 2        # kirish datchigi GPIO
GP_S2      = 6        # chiqish datchigi GPIO
D_MM       = 2000.0   # datchiklar orasidagi masofa, mm  <-- ANIQ O'LCHANG
TEZLIK_ZAX = 20.0     # zaxira tezlik, m/min (xotira bo'sh bo'lganda)
TOL_MM     = 15.0     # ikki natija farqining chegarasi, mm
MIN_US     = 50000    # 50 ms dan qisqa signal shovqin deb tashlanadi
SETTLE_MS  = 300      # detal tugadi deb hisoblash uchun tinchlik
STUCK_S    = 30       # shuncha soniya yopiq tursa - yopishib qolgan
XATO_N     = 3        # ketma-ket javob bermasa - ogohlantirish
IFLOS_N    = 5        # ketma-ket uzunroq bersa - ifloslangan
XOTIRA_N   = 10       # tezlik xotirasining uzunligi
FAOL_PAST  = True     # datchik yopilganda kirish PASTGA tushadimi
CHOP       = True     # Thonny uchun o'qiladigan matn ham chiqsinmi
# ======================================================

navbat = []
st = {1: {'us': None, 'ms': None, 'dur': None, 'yopiq': False, 'stuck': False},
      2: {'us': None, 'ms': None, 'dur': None, 'yopiq': False, 'stuck': False}}

faol       = False
oxirgi_ms  = 0
xotira     = []          # oxirgi tezliklar, mm/us
xato_ket   = {1: 0, 2: 0}
iflos_ket  = {1: 0, 2: 0}
son        = 0


def yopiq_p(p):
    return (p.value() == 0) if FAOL_PAST else (p.value() == 1)


def qur(kanal, gpio):
    p = Pin(gpio, Pin.IN, Pin.PULL_UP)

    def chekka(pin):
        t = time.ticks_us()
        m = time.ticks_ms()
        if yopiq_p(pin):
            navbat.append((kanal, 1, t, m))
        else:
            navbat.append((kanal, 0, t, m))

    p.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=chekka)
    return p


p1 = qur(1, GP_S1)
p2 = qur(2, GP_S2)

try:
    led = Pin("LED", Pin.OUT)
except (TypeError, ValueError):
    led = Pin(25, Pin.OUT)


def ogohlantir(kanal, sabab, qiymat=0):
    print('{"ev":"ogoh","ch":%d,"sabab":"%s","q":%.1f}' % (kanal, sabab, qiymat))
    if CHOP:
        print("  !! DATCHIK %d — %s" % (kanal, sabab))


def tezlik_ol():
    """Xotiradagi o'rtacha tezlik, mm/us."""
    if xotira:
        return sum(xotira) / len(xotira)
    return TEZLIK_ZAX / 60000.0


def detalni_yop():
    global faol, son

    d1 = st[1]['dur']
    d2 = st[2]['dur']

    # ---- tezlik ----
    v = None
    if st[1]['us'] is not None and st[2]['us'] is not None:
        dt = time.ticks_diff(st[2]['us'], st[1]['us'])
        if dt > 0:
            v = D_MM / dt
            xotira.append(v)
            if len(xotira) > XOTIRA_N:
                xotira.pop(0)

    v_ish = v if v else tezlik_ol()
    yangi = 1 if v else 0

    # ---- har bir datchikning natijasi ----
    L1 = v_ish * d1 if d1 else None
    L2 = v_ish * d2 if d2 else None

    # ---- qaror ----
    shubha = 0
    farq = 0.0

    if L1 is not None and L2 is not None:
        farq = abs(L1 - L2)
        if farq <= TOL_MM:
            L = (L1 + L2) / 2.0
            kod = "OK"
            iflos_ket[1] = 0
            iflos_ket[2] = 0
        else:
            L = min(L1, L2)
            kod = "FARQ"
            shubha = 1 if L1 > L2 else 2       # uzunroq bergani shubhali
            iflos_ket[shubha] += 1
            iflos_ket[3 - shubha] = 0
            if iflos_ket[shubha] >= IFLOS_N:
                ogohlantir(shubha, "iflos_bolishi_mumkin", farq)
                iflos_ket[shubha] = 0
        xato_ket[1] = 0
        xato_ket[2] = 0

    elif L1 is not None:
        L, kod, shubha = L1, "FAQAT1", 2
        xato_ket[2] += 1
        xato_ket[1] = 0
        if xato_ket[2] == XATO_N:
            ogohlantir(2, "javob_yoq")

    elif L2 is not None:
        L, kod, shubha = L2, "FAQAT2", 1
        xato_ket[1] += 1
        xato_ket[2] = 0
        if xato_ket[1] == XATO_N:
            ogohlantir(1, "javob_yoq")

    else:
        faol = False
        for k in (1, 2):
            st[k].update({'us': None, 'ms': None, 'dur': None})
        return

    son += 1

    print('{"ev":"olchov","n":%d,"L":%.1f,"kod":"%s","shubha":%d,'
          '"L1":%s,"L2":%s,"d1":%d,"d2":%d,"v":%.3f,"vyangi":%d,"farq":%.1f}'
          % (son, L, kod, shubha,
             ("%.1f" % L1) if L1 is not None else "null",
             ("%.1f" % L2) if L2 is not None else "null",
             d1 or 0, d2 or 0, v_ish * 60000.0, yangi, farq))

    if CHOP:
        print("")
        print("  ------- O'LCHOV #%d  [%s] -------" % (son, kod))
        print("  Tezlik  : %.2f m/min %s" % (v_ish * 60000.0,
                                             "(o'lchandi)" if yangi else "(xotiradan)"))
        if L1 is not None:
            print("  Datchik 1: %.0f mm   (%.1f ms)" % (L1, d1 / 1000.0))
        else:
            print("  Datchik 1: javob yo'q")
        if L2 is not None:
            print("  Datchik 2: %.0f mm   (%.1f ms)" % (L2, d2 / 1000.0))
        else:
            print("  Datchik 2: javob yo'q")
        if shubha:
            print("  Shubhali : DATCHIK %d   (farq %.1f mm)" % (shubha, farq))
        print("  NATIJA   : %.0f mm   (%.1f cm)" % (L, L / 10.0))
        print("  ---------------------------------")
        print("")

    faol = False
    for k in (1, 2):
        st[k].update({'us': None, 'ms': None, 'dur': None})


print("")
print('{"ev":"boot","d_mm":%.0f}' % D_MM)
if CHOP:
    print("=" * 48)
    print("  IKKI DATCHIKLI REZERVLANGAN O'LCHOV")
    print("  Datchik 1: GP%d      Datchik 2: GP%d" % (GP_S1, GP_S2))
    print("  Masofa D : %.0f mm" % D_MM)
    print("  Farq chegarasi: %.0f mm" % TOL_MM)
    print("=" * 48)
    print("  Detalni o'tkazing. To'xtatish: Ctrl+C")
    print("")

while True:
    # ---- navbatni qayta ishlash ----
    while navbat:
        kanal, e, t, m = navbat.pop(0)
        s = st[kanal]

        if e:
            if s['yopiq']:
                continue                    # takroriy chekka
            s['yopiq'] = True
            s['stuck'] = False
            if s['us'] is None:             # shu detal uchun birinchi marta
                s['us'] = t
                s['ms'] = m
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

    # ---- yopishib qolganini aniqlash ----
    for k in (1, 2):
        s = st[k]
        if s['yopiq'] and not s['stuck'] and s['ms'] is not None:
            if time.ticks_diff(hozir, s['ms']) > STUCK_S * 1000:
                s['stuck'] = True
                ogohlantir(k, "yopishib_qolgan")
                s['yopiq'] = False          # e'tibordan chiqaramiz
                s['dur'] = None

    # ---- detal tugadimi ----
    if faol and not st[1]['yopiq'] and not st[2]['yopiq']:
        if time.ticks_diff(hozir, oxirgi_ms) > SETTLE_MS:
            detalni_yop()

    led.value(1 if (st[1]['yopiq'] or st[2]['yopiq']) else 0)
    time.sleep_ms(5)
