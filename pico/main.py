# main.py — KROMKA STANSIYASI KONTROLLERI  (TZ v1.2, proshivka v1.17)
#
# OYOQCHALAR — TZ 3-bo'lim, boshqa pin ishlatilmaydi:
#   GP1  (2-pin)   <- datchik 1 optopara 4-oyoq   (kirish)
#   GP5  (7-pin)   <- datchik 2 optopara 4-oyoq   (chiqish)
#   GP9  (12-pin)  <- RUN optopara 4-oyoq          (uskuna ishlayapti = 10 m/min)
#   GP13 (17-pin)  <- 18 m/min optopara 4-oyoq
#   GP0  (1-pin)   -> rele moduli IN               (lampa, NO kontakt) — YAGONA rele
#                     Modul amalda YUQORI signalda tortadi (2026-09-17 aniqlandi) — RELE_YOQ
#   GP16 (21-pin)  -> R2 10k -> A nuqta -> C1 -> usilitel NL
#   GND            <- barcha optoparalar 3-oyoq, rele DC-, usilitel GND, AL-2402 0V
#
# BUYRUQLAR (brauzerdan, har biri \n bilan tugaydi):
#   QR                          0.5 s da 2 ta tut-tut, lampa birga (125 bor/125 jim x2)
#   ALARM                       avariya rejimi: lampa + tovush birga 1 s yonadi / 1 s o'chadi
#   STOP                        avariyani to'xtatish
#   TEST                        lampa + sirena 1 s
#   KALIB 1  /  KALIB 0         kalibrlash rejimi
#   SET D=.. V10=.. V18=.. K1=.. K2=.. B1=.. B2=.. C=.. TD=.. AO=0|1 HQ=Hz HA=Hz AV=0|1
#   HB                          stansiya yurak urishi (har 1 s), javob yo'q
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
#   K1/K2  har datchikning O'Z vaqt kechikishi, ms  (tezlikka bog'liq emas)
#   B1/B2  har datchikning O'Z uzunlik siljishi, mm (nur kengligi — detalni
#          doim shuncha uzun ko'radi, tezlikka bog'liq emas):
#          L = v*(t - k) - B
#   C      markazlar orasidagi o'tish vaqtiga tuzatma, ms:  dt_mid = D/v + C
#   V10/V18  zaxira tezlik — faqat dt o'lchanmaganda ishlatiladi
#   TD     datchiklar farqi chegarasi, mm
#   AO     avariya signali O'CHIRILGAN (1 = lampa/sirena chalinmaydi)
#          Hodisalar baribir yuboriladi va MES ga yoziladi — faqat
#          ko'rinadigan/eshitiladigan ogohlantirish bosiladi. Sozlash va
#          o'lchov sinovi paytida shovqin qilmasligi uchun.
#   HQ     QR (skaner) signali ohangi, Hz
#   HA     avariya signali ohangi, Hz — QR dan farq qilsin, operator eshitib bilsin
#   AV     avariya OVOZI: 1 yoqiq, 0 o'chiq (ovozsiz rejim). Lampa baribir
#          miltillaydi. Skaner (QR) ovoziga TA'SIR QILMAYDI.
KAL = {'D': 2555.0, 'V10': 10.0, 'V18': 18.0,
       'K1': 0.0, 'K2': 0.0, 'B1': 0.0, 'B2': 0.0, 'C': 0.0, 'TD': 12.0, 'AO': 0.0,
       'HQ': 2500.0, 'HA': 1500.0, 'AV': 1.0}

# SET bilan kelgan qiymatlar flesh xotiraga ham yoziladi: Pico stansiyasiz
# yonsa ham (kompyuter o'chiq) oxirgi kalibrlash bilan o'lchaydi.
KAL_FAYL = 'kal.json'

def kal_yukla():
    try:
        with open(KAL_FAYL) as f:
            d = json.load(f)
        for k in d:
            if k in KAL:
                KAL[k] = float(d[k])
    except (OSError, ValueError):
        pass

def kal_saqla():
    try:
        with open(KAL_FAYL, 'w') as f:
            json.dump(KAL, f)
    except OSError:
        pass

kal_yukla()

# ================= APPARAT =================
def yopiq(p):
    return (p.value() == 0) if FAOL_PAST else (p.value() == 1)

p_run = Pin(GP_RUN, Pin.IN, Pin.PULL_UP)
p_v18 = Pin(GP_V18, Pin.IN, Pin.PULL_UP)
# RELE_YOQ — lampa yonishi uchun GP0 ga beriladigan qiymat. 2026-09-17: kodda Low trigger
# (0 = tortadi) edi, lekin lampa NO kontaktda ovozga TESKARI yonardi — modul yuqori
# signalda tortadi. Lampa NO kontaktga ulanadi: tinch holatda o'chiq, signalda yonadi.
# Modul sakratkichi Low ga qo'yilsa — shu yerni 0 qiling.
RELE_YOQ = 1
rele  = Pin(GP_RELE, Pin.OUT, value=1 - RELE_YOQ)   # boshlanishda lampa o'chiq
buz   = PWM(Pin(GP_AUDIO))
buz.duty_u16(0)
try:
    led = Pin("LED", Pin.OUT)
except (TypeError, ValueError):
    led = Pin(25, Pin.OUT)

# TOVUSH: har signalning o'z ohangi — KAL['HQ'] (skaner) va KAL['HA'] (avariya).
# 2–3 kHz — quloq eng sezgir va kichik dinamik eng baland chiqaradigan oraliq.
# Stansiyadagi "Signal sinovi" dan eshitib tanlanadi va SET bilan keladi.
TON_HZ = int(KAL['HQ'])
buz.freq(TON_HZ)

# Oxirgi holat eslab qolinadi: har 5 ms da PWM ni qayta yozish tovushni
# g'ijirlatadi, releni esa keraksiz qo'zg'atadi. Chastota ham faqat o'zgarganda
# yoziladi — freq() har chaqirilganda PWM qayta boshlanadi va chirsillaydi.
_oxir = {'lampa': None, 'hz': None, 'f': TON_HZ}

def lampa(on):
    on = True if on else False
    if _oxir['lampa'] is not on:
        _oxir['lampa'] = on
        rele.value(RELE_YOQ if on else 1 - RELE_YOQ)

def tovush(hz):
    hz = int(hz) if hz else 0
    if _oxir['hz'] == hz:
        return
    _oxir['hz'] = hz
    if hz:
        if _oxir['f'] != hz:
            _oxir['f'] = hz
            buz.freq(hz)
        buz.duty_u16(32768)
    else:
        buz.duty_u16(0)

def signal(yon, hz=None):
    """Lampa va tovush — DOIM birga, bitta chaqiriqda."""
    tovush((hz or KAL['HQ']) if yon else 0)
    lampa(yon)

# ================= STANSIYA ULANMAGANDA — XOTIRAGA YIG'ISH =================
#
# Stansiya (brauzer) ulangan bo'lsa har 1 s "HB" yuboradi. XOST_MS davomida
# hech qanday buyruq kelmasa — stansiya yo'q (kompyuter/Chrome o'chiq, kabel
# uzilgan): o'lchov va hodisalar ekranga emas, xotiraga yig'iladi. Stansiya
# qayta gapirganda hammasi "eski_ms" (necha ms oldin bo'lgani) bilan yuboriladi.
# Xotira — RAM: Pico ga tok kelib turguncha saqlanadi.
XOST_MS    = 3000
XOTIRA_MAX = 300
YIGILADI   = ('olchov', 'ogoh', 'avariya_toxtash', 'tiqilish', 'uskuna')
XOST       = {'oxir': None, 'yoqolgan': 0}
yigilgan   = []            # (ticks_ms, json matn)

# ---------- QOROVUL (watchdog) ----------
# Dastur biror joyda qotib qolsa (masalan USB yozuvi blokda tursa), qorovul
# taymeri Pico ni qayta yuklaydi: USB qaytadan ro'yxatdan o'tadi, Windows
# porti tiklanadi va stansiya o'zi ulanadi — kabelni sug'urib-ulash shart emas.
# Qorovul FAQAT stansiya bilan ishlay boshlaganda yoqiladi: Thonny yoki
# mpremote bilan ishlaganda yoqilmaydi, aks holda fayl yozish paytida REPL
# to'xtaganda Pico qayta yuklanib, nusxalashni buzardi.
WDT_MS = 8000
_wdt = {'w': None}

def wdt_yoq():
    if _wdt['w'] is None:
        try:
            from machine import WDT
            _wdt['w'] = WDT(timeout=WDT_MS)
        except (ImportError, AttributeError, ValueError, OSError):
            _wdt['w'] = False          # bu platformada yo'q — qayta urinmaymiz

def wdt_boq():
    if _wdt['w']:
        _wdt['w'].feed()

def xost_bor():
    return XOST['oxir'] is not None and time.ticks_diff(time.ticks_ms(), XOST['oxir']) < XOST_MS

def yubor(d):
    # Stansiya jim bo'lsa USB ga UMUMAN yozmaymiz. Sabab: host portni o'qimay
    # qo'ysa (kiosk yopilgan, Windows portni uyquga qo'ygan), CDC buferi to'lib
    # print() butun dasturni qotirib qo'yishi mumkin — Pico o'lchashdan ham
    # to'xtaydi. Muhim hodisalar xotiraga yig'iladi, qolgani (holat, kal,
    # tezlik) tashlanadi: stansiya ulanganda HOLAT bilan hammasini qayta oladi.
    if not xost_bor():
        if d.get('ev') in YIGILADI:
            if len(yigilgan) >= XOTIRA_MAX:
                yigilgan.pop(0)
                XOST['yoqolgan'] += 1
            yigilgan.append((time.ticks_ms(), json.dumps(d)))
        return
    print(json.dumps(d))

def xotirani_yubor():
    hozir = time.ticks_ms()
    print(json.dumps({'ev': 'yigilgan', 'n': len(yigilgan), 'yoqolgan': XOST['yoqolgan']}))
    while yigilgan:
        ms, s = yigilgan.pop(0)
        # JSON oxiridagi "}" oldiga eski_ms qo'shamiz
        print(s[:-1] + ', "eski_ms": %d}' % time.ticks_diff(hozir, ms))
        wdt_boq()                        # 300 tagacha yozuv — qorovul kutsin
    XOST['yoqolgan'] = 0

def xost_gapirdi():
    yangi = not xost_bor()
    XOST['oxir'] = time.ticks_ms()
    wdt_yoq()                            # stansiya bilan ishlayapmiz — qorovul yoqiladi
    if yangi and (yigilgan or XOST['yoqolgan']):
        xotirani_yubor()

def chop(s):
    # Thonny uchun matn. Stansiya bir marta gapirib keyin jim qolgan bo'lsa —
    # yozmaymiz (yubor() dagi sabab bilan bir xil). Thonny da ishlatilganda
    # stansiya umuman bo'lmaydi (XOST['oxir'] is None) — matn ko'rinaveradi.
    if CHOP and (XOST['oxir'] is None or xost_bor()):
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
# bekor   — shu to'silish avariyali to'xtashga tushdi, o'lchanmaydi
# juft_d1 — (faqat D2) D2 dagi detal hali D1 da ham turibdi, navbatda emas (L > D)
kuzat = {1: {'us': None, 'ms': None, 'yopiq': False, 'stuck': False, 'bekor': False},
         2: {'us': None, 'ms': None, 'yopiq': False, 'stuck': False, 'bekor': False,
             'juft_d1': False}}

# D1 dan o'tib bo'lgan, D2 ni kutayotgan detallar navbati (FIFO).
kutuv = []
KUTUV_MAX = 12       # oraliqqa sig'adigan detaldan ko'p bo'lsa — nimadir noto'g'ri

# JUFTLASHNI TEKSHIRISH (v1.16). Bitta detalning D1 va D2 dagi vaqti deyarli
# bir xil bo'ladi. Katta farq — bu boshqa detal: tiqilib birga o'tgan, yoki
# datchik ostida to'xtab qolgan. Linza ifloslanishi millimetr beradi (TD),
# tiqilish esa o'nlab santimetr — shuning uchun chegara keng.
JUFT_TOL  = 0.25     # 25% nisbiy chegara (kichik uzunlikdan)
JUFT_MIN  = 30.0     # kamida shuncha mm — qisqa detallar uchun
TIQ_MAX   = 4        # oraliqqa sig'adigan detal soni (D=2555 mm)
KUT_KARRA = 5        # D2 ni kutish muddati: D/v ning shuncha karrasi (~78 s)

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
    """D1 detalni TUGATGANDAN keyin D2 ham tugatishi uchun eng uzoq vaqt.

    Hisob D1 ning ORQA qirrasidan boshlanadi: orqa qirra D1 dan D2 gacha
    aynan D/v yuradi — detal uzunligiga bog'liq emas. Ilgari hisob D1 ning
    OLD qirrasidan edi, u holda D2 tugashi (D+L)/v bo'ladi va L > ~D/2
    bo'lgan detal (masalan 2740 mm) vaqt tugab FAQAT1 + FAQAT2 ga
    bo'linib ketardi. Nominal D/v, ustiga 50% zaxira.
    """
    if S is None:
        S = S_detal
    v = KAL['V18'] if S == 18 else KAL['V10']
    if v <= 0 or KAL['D'] <= 0:
        return 20000
    return int(KAL['D'] / (v * 1000.0 / 60.0) * 1500.0) + 500

# ================= OGOHLANTIRISH REJIMLARI =================
AL = {'rejim': 'IDLE', 't0': 0}
QR_MS      = 500      # QR: shu vaqt ichida 2 ta tut-tut + 2 ta lampa miltillashi
AVARIYA_MS = 1000     # avariya: shuncha yonadi, shuncha o'chadi

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
    signal(False)
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
        # QR o'qildi: 0.5 s ichida IKKI "tut-tut", lampa ular bilan birga
        # ikki marta yonib-o'chadi: 125 bor / 125 jim / 125 bor / 125 jim.
        # (2026-09-17 foydalanuvchi talabi; ilgari 150/150/150 edi)
        if e < QR_MS:
            signal((e * 4 // QR_MS) % 2 == 0)
        else:
            AL['rejim'] = 'IDLE'; signal(False)
    elif r == 'TEST':
        if e < 1000:
            signal(True)
        else:
            AL['rejim'] = 'IDLE'; signal(False)
    elif r == 'AVARIYA':
        # Lampa va tovush qat'iy BIRGA: 1 s ikkalasi yonadi (bir tekis ohang),
        # 1 s ikkalasi o'chadi — STOP gacha. Ohang almashmaydi: ilgari yongan
        # paytda 800/1200 Hz almashardi, bu chirsillardi va lampa ritmiga mos
        # kelmasdi.
        yon = (e // AVARIYA_MS) % 2 == 0
        tovush(KAL['HA'] if (yon and KAL['AV']) else 0)   # ovozsiz rejimda faqat lampa
        lampa(yon)

def ogoh(ch, sabab, q=0.0):
    yubor({'ev': 'ogoh', 'ch': ch, 'sabab': sabab, 'q': round(q, 2)})
    chop("  !! OGOH: datchik %d — %s" % (ch, sabab))
    avariya_boshla()

# ================= AVARIYALI TO'XTASH =================
#
# Stanok (RUN va 18 m/min kirishlari ikkalasi ham) o'chganda lenta to'xtaydi.
# Shu payt yo'lda detal bo'lsa, uning vaqtlari buziladi — o'lchab bo'lmaydi:
#   1) detal D1 da turibdi (kirishda qiyshaydi, operator STOP bosdi)
#   2) uzun detal D1 va D2 ikkalasida turibdi
#   3) detal D1 dan o'tgan, D2 da turibdi
#   4) detal D1 dan o'tgan, D2 ga yetmagan (oraliqda)
# Har holatda: AVARIYA (lampa+sirena, STOP gacha), hodisa "avariya_toxtash",
# shu detallarning o'lchovi bekor. Bekor detal stanok qayta yongach datchikdan
# chiqib ketsa ham — o'lchov chiqmaydi, FAQAT1/FAQAT2 ham chiqmaydi.
# Stanok o'chiq paytda boshlangan to'silish ham bekor (lekin avariyasiz —
# to'xtash allaqachon qayd qilingan yoki yo'lda detal yo'q edi).
USK_DEB_MS = 200     # RUN kirishi shuncha barqaror tursa — holat o'zgardi deb olinadi
USK = {'holat': None, 'xom': None, 't': 0}

def toxtash_qayd(hozir_ms):
    d1 = kuzat[1]['yopiq']
    d2 = kuzat[2]['yopiq']
    oraliq = len(kutuv) - (1 if (d2 and kutuv) else 0)   # D2 dagisi navbat boshida
    for r in kutuv:
        r['bekor'] = True
    kuzat[1]['bekor'] = d1
    kuzat[2]['bekor'] = d2
    if not (d1 or d2 or kutuv):
        return                               # yo'lda detal yo'q — oddiy to'xtash
    yubor({'ev': 'avariya_toxtash', 'd1': 1 if d1 else 0, 'd2': 1 if d2 else 0,
           'oraliq': oraliq, 'birga': 1 if (d2 and kuzat[2]['juft_d1']) else 0})
    chop("  !! AVARIYALI TO'XTASH: D1=%s D2=%s oraliqda=%d — o'lchov bekor"
         % ('detal' if d1 else '-', 'detal' if d2 else '-', oraliq))
    avariya_boshla()

def qayta_yondi(hozir_ms):
    # To'xtab turgan vaqt kutish/yopishish muddatlariga qo'shilmasin
    for r in kutuv:
        r['ms'] = hozir_ms
    for k in (1, 2):
        if kuzat[k]['yopiq']:
            kuzat[k]['ms'] = hozir_ms

def uskuna_tekshir(hozir_ms):
    x = uskuna_holat()
    if x != USK['xom']:
        USK['xom'] = x
        USK['t'] = hozir_ms
    if USK['holat'] is None:                 # boshlanish — hodisasiz
        USK['holat'] = x
        yubor({'ev': 'uskuna', 'holat': x})
        return
    if x != USK['holat'] and time.ticks_diff(hozir_ms, USK['t']) >= USK_DEB_MS:
        USK['holat'] = x
        yubor({'ev': 'uskuna', 'holat': x})
        chop("  uskuna: %s" % ("ISHLAYAPTI" if x else "to'xtadi"))
        if x:
            qayta_yondi(hozir_ms)
        else:
            toxtash_qayd(hozir_ms)

def ishlayapti():
    return USK['holat'] == 1

def lenta_turibdi():
    # Tasdiqlangan to'xtash VA kirish hozir ham o'chiq. Qayta yonishning birinchi
    # 200 ms ida (kirish yondi, tasdiq hali yo'q) lenta allaqachon yuryapti.
    return USK['holat'] == 0 and uskuna_holat() == 0

# ================= NAVBAT: D1 -> D2 JUFTLASH =================
def d1_tugadi(us, ms, dur, bekor=False):
    """D1 detalni butunlay o'tkazdi — navbatga qo'yamiz, D2 ni kutadi."""
    s2 = kuzat[2]
    if lenta_turibdi():
        # Lenta turibdi — detal oldinga o'tmagan, qo'lda olib tashlangan.
        # Navbatga qo'yilmaydi. Agar shu detal D2 da ham tursa (juft_d1) — D2
        # ochilganda ham navbatdan hech narsa olinmaydi.
        chop("  > D1: detal olib tashlandi (stanok to'xtagan)")
        return
    if s2['yopiq'] and s2['juft_d1']:
        s2['juft_d1'] = False                # uzun detal endi navbatda — D2 shuni oladi
    # Bekor detal ham navbatga qo'yiladi: u D2 dan o'tganda navbatdan chiqib,
    # jimgina tashlanadi — keyingi detallar juftligi siljimaydi.
    # us — old qirra (µs, dt uchun), ms — orqa qirra (kutish muddati shundan)
    kutuv.append({'us': us, 'ms': ms, 'dur': dur, 'S': tezlik_nom(), 'bekor': bekor})
    chop("  > D1 o'tkazdi (%.0f ms)%s, navbatda %d ta"
         % (dur / 1000.0, ' — BEKOR' if bekor else '', len(kutuv)))
    if len(kutuv) > KUTUV_MAX:
        # Oraliqqa sig'adiganidan ko'p to'planib qoldi — eng eskisi yo'qolgan.
        r = kutuv.pop(0)
        if not r['bekor']:
            yakunla(r, None, None)

def _mm(dur_us, S):
    """Nur to'silgan vaqtdan taxminiy uzunlik (mm) — juftlashni tekshirish uchun.
    Aniq o'lchov emas: nominal tezlik bilan, tuzatmalarsiz."""
    v = KAL['V18'] if S == 18 else KAL['V10']
    return dur_us * v / 60000.0

def _yaqin(a, b):
    """Ikki uzunlik bitta detalga tegishli bo'la oladimi.
    Chegara — nisbiy (JUFT_TOL, KICHIGIDAN hisoblanadi) yoki kamida JUFT_MIN mm.
    Kichigidan olinadi: aks holda 400 va 1600 mm ham "yaqin" bo'lib qolardi.
    Linza ifloslanishi millimetrlar beradi (TD), tiqilish esa o'nlab santimetr."""
    return abs(a - b) <= max(JUFT_MIN, JUFT_TOL * min(a, b))

def juftni_tanla(d2_mm):
    """Navbatdan shu D2 o'lchoviga mos yozuvni tanlaydi.

    QAT'IY TARTIB (2026-09-21 talabi): navbat boshi HECH QACHON o'tkazib
    yuborilmaydi. D2 har doim eng eski yozuvni oladi — D1 dan kelgan ma'lumot
    D2 tasdiqlamaguncha navbatda turadi, ustiga yangisi tushmaydi va
    keyingisiga almashtirilmaydi. Yagona istisno: bir necha detal bir-biriga
    tiqilib, D2 dan BIRGA o'tgan bo'lsa — u holda o'sha yozuvlar birga
    yopiladi (aks holda navbat abadiy bir qadam siljib qolardi), lekin ular
    jimgina tashlanmaydi: `tiqilish` hodisasi bilan MES ga xabar beriladi.

    Qaytaradi (turi, yozuvlar):
      'juft'     [r]            — bitta detal, normal juftlik
      'tiqilish' [r1, r2, ...]  — detallar BIRGA o'tgan (bir-biriga tiqilib)
      'mos_yoq'  []             — navbat bo'sh (D1 bu detalni ko'rmagan)
    """
    if not kutuv:
        return ('mos_yoq', [])
    if _yaqin(_mm(kutuv[0]['dur'], kutuv[0]['S']), d2_mm):
        return ('juft', kutuv[:1])
    yigindi = _mm(kutuv[0]['dur'], kutuv[0]['S'])
    for i in range(1, min(len(kutuv), TIQ_MAX)):
        yigindi += _mm(kutuv[i]['dur'], kutuv[i]['S'])
        if _yaqin(yigindi, d2_mm):
            return ('tiqilish', kutuv[:i + 1])
    # Oxirgi chora: navbat boshi mos kelmadi, lekin KEYINGI yozuvlardan biri
    # aniq mos keldi. Demak boshidagi detal(lar) D2 gacha yetib bormagan —
    # yo'ldan olib qo'yilgan yoki chiqib ketgan. Ularni jimgina tashlamaymiz:
    # har biri uchun `tiqilish` (d2_tasdiqlamadi) hodisasi chiqadi, navbat esa
    # qayta tekislanadi — aks holda undan keyingi HAR BIR detal xato juftlanardi.
    for i in range(1, min(len(kutuv), TIQ_MAX + 1)):
        if _yaqin(_mm(kutuv[i]['dur'], kutuv[i]['S']), d2_mm):
            return ('otkazildi', kutuv[:i + 1])
    # Hech qaysisi mos kelmadi — o'lchov ishonchsiz (detal datchik ostida
    # to'xtab qolgan). Yozuv SHU navbat boshidan olinadi: tartib buzilmaydi.
    return ('mos_emas', kutuv[:1])

def tiqilish_qayd(sabab, rlar, d2_mm):
    """O'lchab bo'lmaydigan holat: detallar birga o'tgan yoki datchik ostida
    to'xtab qolgan. Soxta o'lcham chiqarmaymiz — hodisa va avariya beramiz."""
    yubor({'ev': 'tiqilish', 'sabab': sabab, 'n': len(rlar),
           'L2': round(d2_mm, 1),
           'L1': [round(_mm(r['dur'], r['S']), 1) for r in rlar]})
    chop("  !! TIQILISH (%s): D2 %.0f mm, navbatdagi %d ta detal o'lchanmadi"
         % (sabab, d2_mm, len(rlar)))
    avariya_boshla()

def d2_tugadi(us, dur, bekor=False, juft_d1=False):
    """D2 detalni o'tkazdi — navbatdagi ENG ESKI yozuv bilan juftlaymiz.

    Juftlashdan OLDIN uzunliklar solishtiriladi: D1 dagi vaqt D2 dagiga
    yaqin bo'lmasa, bu bitta detal emas (tiqilish, birga o'tish, datchik
    ostida to'xtash). Ilgari tekshiruv yo'q edi va navbat siljiganda har bir
    keyingi o'lchov boshqa detalning D1 yozuvi bilan juftlanib ketardi.
    """
    # Avariyali to'xtashda ilingan detallar: vaqtlari buzilgan (datchik ostida
    # turib qolgan), shuning uchun uzunlik bo'yicha solishtirib bo'lmaydi —
    # navbat tartibi bo'yicha jimgina chiqaramiz.
    if bekor or (kutuv and kutuv[0]['bekor'] and not juft_d1):
        if kutuv and not juft_d1:
            kutuv.pop(0)
        chop("  > D2: detal bekor (avariyali to'xtash)")
        return

    d2_mm = _mm(dur, tezlik_nom())
    if juft_d1:
        turi, rlar = ('mos_yoq', [])
    elif kutuv and kutuv[0]['S'] != tezlik_nom():
        # Detal yo'lda ekan tezlik almashgan — nominal tezlik bilan hisoblangan
        # uzunliklarni solishtirib bo'lmaydi. Navbat tartibiga ishonamiz.
        turi, rlar = ('juft', kutuv[:1])
    else:
        turi, rlar = juftni_tanla(d2_mm)

    for _ in rlar:                       # tanlangan yozuvlar navbatdan chiqadi
        kutuv.pop(0)

    if any(r['bekor'] for r in rlar):
        chop("  > D2: detal bekor (avariyali to'xtash)")
        return

    if turi == 'juft':
        yakunla(rlar[0], dur, us)
        return
    if turi == 'tiqilish':
        tiqilish_qayd('birga_otdi', rlar, d2_mm)
        return
    if turi == 'otkazildi':              # oldingilari D2 gacha yetmagan, oxirgisi mos
        tiqilish_qayd('d2_tasdiqlamadi', rlar[:-1], d2_mm)
        yakunla(rlar[-1], dur, us)
        return
    if turi == 'mos_emas':               # navbat boshi olindi, lekin vaqtlar mos emas
        tiqilish_qayd('vaqt_mos_emas', rlar, d2_mm)
        return
    yakunla(None, dur, us)               # mos_yoq: navbat bo'sh — D1 ko'rmagan (FAQAT2)

def kutuvni_tekshir(hozir_ms):
    """Navbatni kuzatadi. VAQT BO'YICHA HECH NARSA TASHLANMAYDI (2026-09-21).

    Tarix: v1.15 gacha navbat boshi `d2_kutish_ms` (10 m/min da ~23 s) dan
    uzoq kutsa yozuv TASHLANARDI. Tiqilishda shu tashlash navbatni bir qadam
    siljitib, keyingi har bir D2 o'lchovini boshqa detalning D1 yozuvi bilan
    juftlardi. v1.16 da muddat uzaytirilgan edi, endi esa butunlay olib
    tashlandi: D1 dan kelgan yozuv D2 tasdiqlamaguncha navbatda TURADI.

    Uzoq kutish faqat OGOHLANTIRISH sababi: D2 datchigi javob bermayotgan
    bo'lishi mumkin. Navbat esa `KUTUV_MAX` oshgandagina qisqaradi
    (`d1_tugadi` ichida) — ya'ni oraliqqa sig'maydigan darajada to'planganda.
    """
    if not ishlayapti() or not kutuv:
        return                           # lenta turibdi — kutish hisoblanmaydi
    if kuzat[1]['yopiq'] or kuzat[2]['yopiq']:
        return                           # datchik ostida detal turibdi — tiqilish
    r = kutuv[0]
    if r.get('ogoh'):
        return                           # bu yozuv uchun allaqachon ogohlantirdik
    if time.ticks_diff(hozir_ms, r['ms']) > d2_kutish_ms(r['S']) * KUT_KARRA:
        r['ogoh'] = True
        ogoh(2, 'javob_yoq', len(kutuv))

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
        if v_eff_S > 0 and abs(v_olch - v_eff_S) / v_eff_S * 100.0 > TOL_TEZLIK:
            # O'lchangan tezlik nominaldan juda uzoq — ishonchsiz. Shunday
            # bo'ladi: detal D1 dan o'tib, oraliqda tiqilib turib qoladi, keyin
            # yo'lida davom etadi — dt shu turgan vaqtni ham o'z ichiga oladi.
            # Detalning O'ZI datchik ostidan to'liq tezlikda o'tgan, shuning
            # uchun t1/t2 to'g'ri: uzunlikni NOMINAL tezlik bilan hisoblaymiz.
            ogoh(0, 'tezlik_nomuvofiq', v_olch)
            v_mm_us = v_eff_S / 60000.0
        else:
            yangi = 1
            xotira.append(v_olch)
            if len(xotira) > XOTIRA_N:
                xotira.pop(0)
    else:
        v_mm_us = v_eff_S / 60000.0

    L1 = v_mm_us * (d1 - KAL['K1'] * 1000.0) - KAL['B1'] if d1 else None
    L2 = v_mm_us * (d2 - KAL['K2'] * 1000.0) - KAL['B2'] if d2 else None

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
    xost_gapirdi()                       # har qanday buyruq — stansiya tirik
    cmd = q[0].upper()
    if cmd == 'HB':
        pass                             # stansiya yurak urishi (1 s) — javobsiz
    elif cmd == 'QR':
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
        eski = dict(KAL)
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
        if KAL != eski:
            kal_saqla()                  # flesh — faqat o'zgarganda (yeyilmasin)
        d = dict(KAL); d['ev'] = 'kal'
        yubor(d)
        chop("  kalibrlash saqlandi: D=%.2f V10=%.3f V18=%.3f K1=%.3f K2=%.3f B1=%.2f B2=%.2f C=%.3f TD=%.1f"
             % (KAL['D'], KAL['V10'], KAL['V18'], KAL['K1'], KAL['K2'], KAL['B1'], KAL['B2'], KAL['C'], KAL['TD']))
        chop("  avariya signali: %s, ovozi: %s, ohang QR %d Hz / avariya %d Hz" % ("O'CHIQ" if KAL['AO'] else 'yoniq', 'yoniq' if KAL['AV'] else "O'CHIQ", KAL['HQ'], KAL['HA']))
    elif cmd == 'PING':
        yubor({'ev': 'pong', 'up': time.ticks_ms()})
    elif cmd == 'HOLAT':
        d = dict(KAL)
        d.update({'ev': 'holat', 'alarm': 1 if AL['rejim'] == 'AVARIYA' else 0,
                  'uskuna': uskuna_holat(), 'v_nom': tezlik_nom(),
                  'kalib': 1 if kalib_rejim else 0, 'n': son, 'navbat': len(kutuv),
                  'ver': '1.17'})
        yubor(d)

# ================= BOSHLANISH =================
yubor({'ev': 'boot', 'D': KAL['D'], 'V10': KAL['V10'], 'V18': KAL['V18']})
if CHOP:
    print("=" * 50)
    print("  KROMKA STANSIYASI KONTROLLERI  v1.17")
    print("  D1=GP%d  D2=GP%d  RUN=GP%d  V18=GP%d  RELE=GP%d  AUDIO=GP%d"
          % (GP_D1, GP_D2, GP_RUN, GP_V18, GP_RELE, GP_AUDIO))
    print("  Buyruqlar: QR ALARM STOP TEST KALIB SET PING HOLAT HB")
    print("=" * 50)

v_old = -1

# ================= ASOSIY SIKL =================
def qadam():
    """Asosiy siklning bitta aylanishi (sinov uchun alohida chaqirsa bo'ladi)."""
    global S_detal, v_old
    buyruq_tekshir()

    # Uskuna holati datchik chekkalaridan OLDIN: to'xtash qayd qilinsa,
    # shu aylanishdagi chekkalar allaqachon to'xtagan holatda talqin qilinadi.
    uskuna_tekshir(time.ticks_ms())

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
            # Stanok o'chiq paytda boshlangan to'silish — o'lchanmaydi
            s['bekor'] = lenta_turibdi()
            if kanal == 1:
                S_detal = tezlik_nom()
            else:
                # Navbat bo'sh, D1 esa yopiq — D2 ga D1 dagi o'sha uzun detal keldi
                s['juft_d1'] = (not kutuv) and kuzat[1]['yopiq']
                if s['juft_d1'] and kuzat[1]['bekor']:
                    s['bekor'] = True
        else:
            if not s['yopiq']:
                continue
            s['yopiq'] = False
            bekor = s['bekor'] or lenta_turibdi()
            s['bekor'] = False
            if s['us'] is None:
                continue
            d = time.ticks_diff(t, s['us'])
            s['us'] = None
            if d < MIN_US:
                continue                      # shovqin — hisobga olinmaydi (navbatga ham tegmaydi)
            if kanal == 1:
                d1_tugadi(time.ticks_add(t, -d), m, d, bekor)   # m — orqa qirra lahzasi
            else:
                juft = s['juft_d1']
                s['juft_d1'] = False
                d2_tugadi(time.ticks_add(t, -d), d, bekor, juft)

    hozir = time.ticks_ms()

    # Yopishib qolish — faqat stanok ishlayotganda (to'xtaganda detal turishi normal)
    if ishlayapti():
        for k in (1, 2):
            s = kuzat[k]
            if s['yopiq'] and not s['stuck'] and s['ms'] is not None:
                if time.ticks_diff(hozir, s['ms']) > STUCK_S * 1000:
                    s['stuck'] = True
                    s['yopiq'] = False
                    s['us'] = None
                    s['bekor'] = False
                    ogoh(k, 'yopishib_qolgan')

    # D2 ga yetib bormagan detallar bormi
    kutuvni_tekshir(hozir)

    v = tezlik_nom()
    if v != v_old:
        v_old = v
        yubor({'ev': 'tezlik', 'v': v})
        chop("  tezlik: %d m/min" % v)

    alarm_tick()
    led.value(1 if (kuzat[1]['yopiq'] or kuzat[2]['yopiq']) else 0)
    wdt_boq()

if __name__ == '__main__':
    while True:
        qadam()
        time.sleep_ms(5)

