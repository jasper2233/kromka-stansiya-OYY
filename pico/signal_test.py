# signal_test.py — QR VA AVARIYA SIGNALLARINI O'LCHASH
#
# main.py ning haqiqiy kodini yuklab, rele (GP0) va tovush (GP16) holatini
# 5 ms qadam bilan o'qiydi va vaqtlarini o'lchaydi. Signal xatti-harakati
# o'zgarmaganini tekshirish uchun.
#
# KUTILGAN NATIJA
#   QR      : 0.5 s ichida lampa va tovush birga 2 marta (125 bor / 125 jim x2)
#   AVARIYA : lampa va tovush aynan bir vaqtda, 1 s yonadi / 1 s o'chadi, ohang bir xil
#
# ISHGA TUSHIRISH
#   Thonny da  : ochib Run (F5). main.py Pico da bo'lishi shart.
#   Kompyuterdan: python -m mpremote connect COM6 run pico/signal_test.py  (port raqamini tekshiring)
#
# DIQQAT: sinov vaqtida lampa haqiqatan yonadi va sirena chaladi (~6 s).
# Sinovdan keyin Pico ni qayta yuklang (Thonny: Stop/Restart) — main.py ishlashi uchun.

import time

src = open('main.py').read()
kes = src.index('# ================= ASOSIY SIKL =================')
G = {}
exec(src[:kes], G)

rele = G['rele']
YOQ = G['RELE_YOQ']
buz = G['buz']
alarm_tick = G['alarm_tick']
KAL = G['KAL']
KAL['AO'] = 0.0; KAL['AV'] = 1.0          # sinov vaqtida signal va ovoz yoqiq
xato = 0


def tekshir(shart, matn):
    global xato
    if shart:
        print('  ok  :', matn)
    else:
        xato += 1
        print('  XATO:', matn)


def kuzat(davomiylik):
    """(vaqt_ms, lampa_yoniqmi, tovush_bormi) ro'yxati"""
    tarix = []
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < davomiylik:
        alarm_tick()
        tarix.append((time.ticks_diff(time.ticks_ms(), t0),
                      rele.value() == YOQ,
                      buz.duty_u16() > 0))
        time.sleep_ms(5)
    return tarix


def bosqichlar(tarix, idx):
    """holat o'zgargan joylarni (vaqt, holat) ro'yxati qilib qaytaradi"""
    b = []
    oxirgi = None
    for q in tarix:
        if q[idx] != oxirgi:
            b.append((q[0], q[idx]))
            oxirgi = q[idx]
    return b


print('')
print('=' * 58)
print('  SIGNALLARNI HAQIQIY APPARATDA O\'LCHASH')
print('  Lampa yonadi va tovush chiqadi - qarang va eshiting!')
print('=' * 58)

# ---------------- QR ----------------
print('')
print('--- QR SIGNALI ---')
G['qr_boshla']()
t = kuzat(650)
lam = bosqichlar(t, 1)
tov = bosqichlar(t, 2)
print('  lampa  :', lam)
print('  tovush :', tov)

nomuvofiq = [q for q in t if q[1] != q[2]]
tekshir(len(nomuvofiq) == 0, 'lampa va tovush HAR LAHZADA birga (%d nomuvofiq lahza)' % len(nomuvofiq))
yonish = len([1 for i in range(len(lam)) if lam[i][1]])
tekshir(yonish == 2, 'lampa IKKI marta yondi — rele 2 marta tortdi (topildi: %d)' % yonish)
gudok = len([1 for i in range(len(tov)) if tov[i][1]])
tekshir(gudok == 2, 'tovush IKKI marta chiqdi (topildi: %d)' % gudok)
tekshir(all(not q[1] and not q[2] for q in t if q[0] >= 520), '520 ms dan keyin ikkalasi ham o\'chdi')
yon_ms = [b[0] for b in lam if b[1]]
tekshir(len(yon_ms) == 2 and yon_ms[1] - yon_ms[0] <= 280, 'ikki tut-tut orasi ~250 ms (topildi: %s)' % yon_ms)
tekshir(buz.freq() == int(KAL['HQ']), 'skaner ohangi %d Hz (topildi: %d)' % (KAL['HQ'], buz.freq()))

# ---------------- AVARIYA ----------------
print('')
print('--- AVARIYA SIGNALI (4 s) ---')
G['avariya_boshla']()
t = kuzat(4200)
lam = bosqichlar(t, 1)
tov = bosqichlar(t, 2)
print('  lampa  :', lam)
print('  tovush :', tov)

nomuvofiq = [q for q in t if q[1] != q[2]]
tekshir(len(nomuvofiq) == 0,
        'lampa va tovush HAR LAHZADA birga (%d nomuvofiq lahza)' % len(nomuvofiq))
tekshir(len(lam) >= 4, 'lampa yonib-o\'chdi (%d o\'zgarish)' % len(lam))
tekshir(buz.freq() == int(KAL['HA']), 'avariya ohangi %d Hz, skanerdan farqli (topildi: %d)' % (KAL['HA'], buz.freq()))
G['avariya_toxtat']()
tekshir(rele.value() != YOQ and buz.duty_u16() == 0, 'STOP dan keyin lampa va tovush o\'chdi')

# ---------------- AVARIYA OVOZSIZ ----------------
print('')
print('--- AVARIYA OVOZSIZ REJIMI (2.2 s): lampa bor, ovoz yo''q ---')
KAL['AV'] = 0.0
G['avariya_boshla']()
t = kuzat(2200)
tekshir(any(q[1] for q in t), 'lampa miltilladi')
tekshir(not any(q[2] for q in t), 'ovoz chiqmadi')
G['avariya_toxtat']()
G['qr_boshla']()
t = kuzat(650)
tekshir(len([1 for q in bosqichlar(t, 2) if q[1]]) == 2, 'ovozsiz rejimda ham skaner 2 marta tut-tut dedi')
KAL['AV'] = 1.0

# ---------------- QR avariyadan keyin ----------------
print('')
print('--- STOP dan keyin QR yana ishlaydimi ---')
G['qr_boshla']()
t = kuzat(650)
gudok = len([1 for i, q in enumerate(bosqichlar(t, 2)) if q[1]])
tekshir(gudok == 2, 'QR yana ikki marta gudok berdi (topildi: %d)' % gudok)

rele.value(1 - YOQ)
buz.duty_u16(0)
print('')
print('=' * 58)
print('  NATIJA: ' + ('HAMMASI O\'TDI' if xato == 0 else '%d TA XATO' % xato))
print('=' * 58)
