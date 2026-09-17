# tekshir.py — KIRISHLARNI JONLI KUZATISH
#
# Bu dastur hech narsa hisoblamaydi. U to'rtta kirish oyoqchasining
# holatini har yarim soniyada ko'rsatadi va o'zgarishlarni sanaydi.
#
# OYOQCHALAR (haqiqiy montaj)
#   GP1  (2-pin)   <- datchik 1 optopara 4-oyoq   (kirish)
#   GP5  (7-pin)   <- datchik 2 optopara 4-oyoq   (chiqish)
#   GP9  (12-pin)  <- RUN optopara 4-oyoq          (uskuna ishlayapti)
#   GP13 (17-pin)  <- 18 m/min optopara 4-oyoq
#
# Thonny da oching -> Run (F5). Shell da raqamlar oqib chiqa boshlaydi.
#
# NIMA KO'RISH KERAK
#   Bo'sh holat       : hammasi 1
#   Signal kelganda   : tegishli raqam 0 ga o'zgaradi
#
# TEST: oddiy sim bilan GP1 ni GND ga tegizing — raqam 1 dan 0 ga tushishi kerak.
#       Tushmasa — ayb Pico da emas, optopara yoki simda.

from machine import Pin
import time

KIRISH = (("D1  GP1", 1), ("D2  GP5", 5), ("RUN GP9", 9), ("V18 GP13", 13))

pinlar = [(nom, Pin(g, Pin.IN, Pin.PULL_UP)) for nom, g in KIRISH]
oldingi = [None] * len(pinlar)
sanoq = [0] * len(pinlar)

print("")
print("=" * 58)
print("  KIRISHLARNI KUZATISH")
print("  1 = bo'sh holat       0 = signal bor")
print("  To'xtatish: Ctrl+C")
print("=" * 58)
print("")

while True:
    qiymat = [p.value() for _, p in pinlar]

    belgi = ""
    for i in range(len(pinlar)):
        if oldingi[i] is not None and qiymat[i] != oldingi[i]:
            sanoq[i] += 1
            belgi += "   <<< %s O'ZGARDI (jami %d)" % (pinlar[i][0], sanoq[i])
        oldingi[i] = qiymat[i]

    qator = "  ".join("%s = %d" % (pinlar[i][0], qiymat[i]) for i in range(len(pinlar)))
    print("  " + qator + belgi)
    time.sleep(0.5)
