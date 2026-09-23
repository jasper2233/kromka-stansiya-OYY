# signal_test.py — QR VA AVARIYA SIGNALLARINI O'LCHASH
#
# main.py ning haqiqiy kodini yuklab, rele (GP0) holatini 5 ms qadam bilan
# o'qiydi va vaqtlarini o'lchaydi. Signal xatti-harakati o'zgarmaganini
# tekshirish uchun.
#
# v1.20 dan Pico OVOZ CHIQARMAYDI (tovush MES tomonida). Shuning uchun sinov:
#   - lampa vaqtlarini o'lchaydi (ilgarigidek),
#   - GP16 doim PAST turganini tekshiradi (usilitel kirishi jim),
#   - rele har almashishida "sig" hodisasi ketganini tekshiradi — MES ovozni
#     aynan shundan boshlaydi, faza shu bilan bir xil bo'ladi.
#
# KUTILGAN NATIJA
#   QR      : 0.5 s ichida lampa 2 marta (125 bor / 125 jim x2), 4 ta sig
#   AVARIYA : lampa 1 s yonadi / 1 s o'chadi, har almashishda sig
#
# ISHGA TUSHIRISH
#   Thonny da  : ochib Run (F5). main.py Pico da bo'lishi shart.
#   Kompyuterdan: python -m mpremote connect COM6 run pico/signal_test.py  (port raqamini tekshiring)
#
# DIQQAT: sinov vaqtida lampa haqiqatan yonadi (~6 s), ovoz chiqmaydi.
# Sinovdan keyin Pico ni qayta yuklang (Thonny: Stop/Restart) — main.py ishlashi uchun.

import time

src = open('main.py').read()
kes = src.index('# ================= ASOSIY SIKL =================')
G = {}
exec(src[:kes], G)

rele = G['rele']
YOQ = G['RELE_YOQ']
audio = G['audio']                        # GP16 — v1.20 dan doim past
alarm_tick = G['alarm_tick']
KAL = G['KAL']
KAL['AO'] = 0.0                           # sinov vaqtida signal yoqiq
xato = 0

# "sig" hodisalarini tutib olamiz: yubor() ni almashtiramiz (stansiya ulanmagan
# bo'lsa u xotiraga yig'ardi va biz ko'rmasdik).
SIG = []
_asl_yubor = G['yubor']
def _yubor(d):
    if d.get('ev') == 'sig':
        SIG.append(d)
G['yubor'] = _yubor


def tekshir(shart, matn):
    global xato
    if shart:
        print('  ok  :', matn)
    else:
        xato += 1
        print('  XATO:', matn)


def kuzat(davomiylik):
    """(vaqt_ms, lampa_yoniqmi, GP16_holati) ro'yxati"""
    tarix = []
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < davomiylik:
        alarm_tick()
        tarix.append((time.ticks_diff(time.ticks_ms(), t0),
                      rele.value() == YOQ,
                      audio.value()))
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
print('  Lampa yonadi - qarang! (ovoz v1.20 dan MES tomonida)')
print('=' * 58)

# ---------------- QR ----------------
print('')
print('--- QR SIGNALI ---')
del SIG[:]
G['qr_boshla']()
t = kuzat(650)
lam = bosqichlar(t, 1)
print('  lampa  :', lam)
print('  sig    :', [(d['r'], d['on'], d['ms']) for d in SIG])

yonish = len([1 for i in range(len(lam)) if lam[i][1]])
tekshir(yonish == 2, 'lampa IKKI marta yondi — rele 2 marta tortdi (topildi: %d)' % yonish)
tekshir(all(q[2] == 0 for q in t), 'GP16 doim past — usilitel jim')
tekshir(all(not q[1] for q in t if q[0] >= 520), '520 ms dan keyin lampa o\'chdi')
yon_ms = [b[0] for b in lam if b[1]]
tekshir(len(yon_ms) == 2 and yon_ms[1] - yon_ms[0] <= 280, 'ikki miltillash orasi ~250 ms (topildi: %s)' % yon_ms)
tekshir([d['on'] for d in SIG] == [1, 0, 1, 0], 'sig: yondi-o\'chdi x2 (topildi: %s)' % [d['on'] for d in SIG])
tekshir(all(d['r'] == 'qr' for d in SIG), 'sig rejimi "qr"')
tekshir(all(d['ms'] == 125 for d in SIG if d['on']), 'sig ms = 125 (MES tovush uzunligini shundan oladi)')

# ---------------- AVARIYA ----------------
print('')
print('--- AVARIYA SIGNALI (4 s) ---')
del SIG[:]
G['avariya_boshla']()
t = kuzat(4200)
lam = bosqichlar(t, 1)
print('  lampa  :', lam)
print('  sig    :', [(d['r'], d['on'], d['ms']) for d in SIG])

tekshir(len(lam) >= 4, 'lampa yonib-o\'chdi (%d o\'zgarish)' % len(lam))
tekshir(all(q[2] == 0 for q in t), 'GP16 doim past — usilitel jim')
# Faza: har lampa o'zgarishiga AYNAN bitta sig to'g'ri kelishi shart, aks holda
# MES dagi ovoz lampadan oldin/keyin qolib ketadi.
tekshir(len(SIG) == len(lam), 'har lampa o\'zgarishiga bitta sig (lampa %d, sig %d)' % (len(lam), len(SIG)))
tekshir([d['on'] for d in SIG] == [1 if b[1] else 0 for b in lam], 'sig va lampa ketma-ketligi bir xil')
tekshir(all(d['r'] == 'avariya' for d in SIG), 'sig rejimi "avariya"')
tekshir(all(d['ms'] == 1000 for d in SIG if d['on']), 'sig ms = 1000')
G['avariya_toxtat']()
del SIG[:]
tekshir(rele.value() != YOQ, 'STOP dan keyin lampa o\'chdi')

# ---------------- TEST ----------------
print('')
print('--- TEST SIGNALI (1 s) ---')
del SIG[:]
G['test_boshla']()
t = kuzat(1300)
on = [q[0] for q in t if q[1]]
tekshir(bool(on) and on[-1] - on[0] >= 950, 'lampa ~1 s yondi (topildi: %d ms)' % (on[-1] - on[0] if on else 0))
tekshir([d['on'] for d in SIG] == [1, 0], 'sig: yondi va o\'chdi (topildi: %s)' % [d['on'] for d in SIG])
tekshir(all(q[2] == 0 for q in t), 'GP16 doim past — usilitel jim')

# ---------------- QR avariyadan keyin ----------------
print('')
print('--- STOP dan keyin QR yana ishlaydimi ---')
del SIG[:]
G['qr_boshla']()
t = kuzat(650)
yonish = len([1 for q in bosqichlar(t, 1) if q[1]])
tekshir(yonish == 2, 'QR yana ikki marta miltilladi (topildi: %d)' % yonish)
tekshir(len(SIG) == 4, 'QR sig hodisalari yana ketdi (topildi: %d)' % len(SIG))

rele.value(1 - YOQ)
audio.value(0)
print('')
print('=' * 58)
print('  NATIJA: ' + ('HAMMASI O\'TDI' if xato == 0 else '%d TA XATO' % xato))
print('=' * 58)
