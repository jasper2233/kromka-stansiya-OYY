# test_pico.py — SINOV REJIMI
#
# Server ham, brauzer ham kerak emas. Thonny da ochib "Run" bosing —
# natijalar to'g'ridan-to'g'ri Shell oynasida chiqadi.
#
# ULANISH
#   GP1 (2-pin)  <- 1-optopara 4-oyoq   (kirish datchigi)
#   GP5 (7-pin)  <- 2-optopara 4-oyoq   (chiqish datchigi)
#   GND (3-pin)  <- ikkala optoparaning 3-oyogi
#
# DATCHIKSIZ SINASH
#   Oddiy sim bilan GP1 ni GND ga bir soniya tegizib turing va uzing —
#   dastur buni "detal o'tdi" deb hisoblaydi va uzunlikni chiqaradi.

from machine import Pin
import time

# =========== SOZLAMALAR ===========
DATCHIK_1 = 1        # GPIO raqami, kirish datchigi
DATCHIK_2 = 5        # GPIO raqami, chiqish datchigi
IKKI      = True     # True = 2 datchik, tezlik o'lchanadi
                     # False = 1 datchik, quyidagi TEZLIK ishlatiladi
D_MM      = 2000.0   # datchiklar orasidagi masofa, mm
TEZLIK    = 20.0     # m/min, faqat IKKI = False bo'lganda
K_MS      = 0.0      # kechikish tuzatmasi, ms
MIN_MS    = 50       # bundan qisqa signal shovqin deb tashlanadi
FAOL_PAST = True     # datchik yopilganda kirish PASTGA tushadimi
# ==================================

navbat = []
ochiq  = {}
S      = {'kirish': None, 'v': None}
olchovlar = []


def yopiq(p):
    return (p.value() == 0) if FAOL_PAST else (p.value() == 1)


def qur(kanal, gpio):
    p = Pin(gpio, Pin.IN, Pin.PULL_UP)

    def chekka(pin):
        t = time.ticks_us()
        if yopiq(pin):
            if kanal in ochiq:
                return
            ochiq[kanal] = t
            if kanal == 1:
                S['kirish'] = t
                navbat.append(('kirdi', 0))
            elif S['kirish'] is not None:
                dt = time.ticks_diff(t, S['kirish'])
                if dt > 0:
                    navbat.append(('tezlik', dt))
        else:
            t0 = ochiq.pop(kanal, None)
            if t0 is not None and kanal == 1:
                navbat.append(('chiqdi', time.ticks_diff(t, t0)))

    p.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=chekka)
    return p


p1 = qur(1, DATCHIK_1)
p2 = qur(2, DATCHIK_2)

try:
    led = Pin("LED", Pin.OUT)
except (TypeError, ValueError):
    led = Pin(25, Pin.OUT)

print("")
print("=" * 46)
print("  UZUNLIK O'LCHASH - SINOV REJIMI")
print("  Datchik 1: GP%d      Datchik 2: GP%d" % (DATCHIK_1, DATCHIK_2))
if IKKI:
    print("  Rejim: 2 datchik, D = %.0f mm" % D_MM)
else:
    print("  Rejim: 1 datchik, tezlik = %.1f m/min" % TEZLIK)
print("=" * 46)
print("  Detalni o'tkazing. To'xtatish: Ctrl+C")
print("")

while True:
    while navbat:
        turi, v = navbat.pop(0)

        if turi == 'kirdi':
            S['v'] = None
            print("  > detal 1-datchikda")

        elif turi == 'tezlik':
            S['v'] = (D_MM / (v / 1000.0)) * 60.0
            print("  > 2-datchikka yetdi, tezlik %.2f m/min" % S['v'])

        elif turi == 'chiqdi':
            t_ms = v / 1000.0

            if t_ms < MIN_MS:
                print("  ! juda qisqa (%.0f ms) - shovqin deb tashlandi" % t_ms)
                print("")
                continue

            if IKKI and S['v']:
                tezlik = S['v']
            else:
                tezlik = TEZLIK
                if IKKI:
                    print("  ! 2-datchik ishlamadi - qo'lda tezlik ishlatildi")

            mm = (tezlik / 60.0) * (t_ms - K_MS)
            olchovlar.append(mm)
            n = len(olchovlar)

            print("")
            print("  ------- O'LCHOV #%d -------" % n)
            print("  Vaqt    : %.1f ms" % t_ms)
            print("  Tezlik  : %.2f m/min" % tezlik)
            print("  UZUNLIK : %.0f mm   (%.1f cm)" % (mm, mm / 10.0))

            if n >= 2:
                mn = min(olchovlar)
                mx = max(olchovlar)
                ort = sum(olchovlar) / n
                print("  ---")
                print("  Seriya  : n=%d  o'rtacha=%.1f mm" % (n, ort))
                print("  Tarqoq  : %.1f ... %.1f  =  +/- %.1f mm"
                      % (mn, mx, (mx - mn) / 2.0))
            print("  --------------------------")
            print("")

    led.value(1 if ochiq else 0)
    time.sleep_ms(5)
