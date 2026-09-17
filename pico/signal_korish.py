# signal_korish.py — SIGNALLARNI KO'Z VA QULOQ BILAN TEKSHIRISH (sekin ketma-ketlik)
#
# signal_test.py dan farqi: vaqt o'lchamaydi, operator lampa va ovozni ko'rib-eshitib
# ulgurishi uchun signallar orasida pauza bor. Umumiy ~52 s.
#
#   0–10 s   tinch — lampa o'chiq
#   10,15,20 skaner signali (2 tut-tut + lampa 2 marta)
#   25–33 s  avariya, ovoz bilan (1 s yonadi / 1 s o'chadi)
#   38–46 s  avariya ovozsiz — faqat lampa
#   48 s     skaner signali (ovozsiz rejimda ham chalinadi)
#
# Kompyuterdan: python -m mpremote connect COM6 run pico/signal_korish.py
# Keyin Pico ni qayta yuklang (mpremote ... reset) — main.py ishlashi uchun.

import time

src = open('main.py').read()
G = {}
exec(src[:src.index('# ================= ASOSIY SIKL =================')], G)
KAL = G['KAL']
KAL['AO'] = 0.0
KAL['AV'] = 1.0


def kut(soniya):
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < soniya * 1000:
        G['alarm_tick']()
        time.sleep_ms(5)


def ayt(t, matn):
    print('%4d s  %s' % (t, matn))


ayt(0, 'tinch — lampa O\'CHIQ bo\'lishi kerak')
kut(10)
for t in (10, 15, 20):
    ayt(t, 'SKANER signali: 2 tut-tut, lampa 2 marta')
    G['qr_boshla']()
    kut(5)
ayt(25, 'AVARIYA (ovoz bilan): lampa va ovoz birga 1 s / 1 s')
G['avariya_boshla']()
kut(8)
G['avariya_toxtat']()
ayt(33, 'tinch')
kut(5)
ayt(38, 'AVARIYA OVOZSIZ: faqat lampa miltillaydi')
KAL['AV'] = 0.0
G['avariya_boshla']()
kut(8)
G['avariya_toxtat']()
kut(2)
ayt(48, 'SKANER signali (ovozsiz rejimda ham ovoz chiqadi)')
G['qr_boshla']()
kut(2)
KAL['AV'] = 1.0
G['signal'](False)
ayt(50, 'TUGADI — lampa o\'chiq')
