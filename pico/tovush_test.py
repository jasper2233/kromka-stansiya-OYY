# tovush_test.py — TOVUSH ZANJIRINI BOSQICHMA-BOSQICH TEKSHIRISH
#
# Muammo: usilitel tovush bermayapti. Bu dastur GP16 ni ma'lum holatlarga
# qo'yadi va ushlab turadi — siz shu vaqtda multimetr bilan o'lchaysiz.
# Hech narsa hisoblamaydi, faqat sinov signali beradi.
#
# ZANJIR
#   Pico GP16 (21-pin) --R2 10k--> A nuqta --R3 3.3k--> Pico GND
#                                  A nuqta --C1 10uF (+ A tomonda)--> USIL NL
#   USIL GND (NL yonidagi) -> Pico GND     (signal yeri — SHART)
#   USIL VCC / GND         -> AL-2402 +24 V / 0 V
#   USIL SPL+ / SPL-       -> dinamik
#
# MULTIMETR
#   Qora shchup — HAR DOIM Pico GND da (38-pin yoki 3-pin).
#   Qizil shchup — o'lchanadigan nuqtada. Kutilgan qiymat har bosqichda yoziladi.
#
# ISHLATISH: Thonny da oching -> Run (F5). Har bosqichdan keyin Shell ga Enter.
#            To'xtatish: Ctrl+C.

from machine import Pin, PWM
import time

GP_AUDIO = 16
GP_RELE  = 0

pwm = None


def statik(v):
    """PWM ni o'chirib, oyoqchani doimiy 0 yoki 1 ga qo'yadi."""
    global pwm
    if pwm is not None:
        pwm.duty_u16(0)
        pwm.deinit()
        pwm = None
    Pin(GP_AUDIO, Pin.OUT, value=v)


def tovush(hz, foiz=50):
    """PWM beradi. foiz — to'ldirish koeffitsienti, %."""
    global pwm
    if pwm is None:
        pwm = PWM(Pin(GP_AUDIO))
    pwm.freq(int(hz))
    pwm.duty_u16(int(65535 * foiz / 100))


def ochir():
    global pwm
    if pwm is not None:
        pwm.duty_u16(0)
    else:
        statik(0)


def bosqich(n, nom, izoh):
    print("")
    print("  --- %d-BOSQICH: %s" % (n, nom))
    for s in izoh:
        print("      " + s)


def pauza():
    try:
        input("      >>> o'lchab bo'lgach Enter: ")
    except (KeyboardInterrupt, EOFError):
        raise SystemExit


print("")
print("=" * 58)
print("  TOVUSH ZANJIRINI TEKSHIRISH   GP%d -> R2 -> A -> C1 -> NL" % GP_AUDIO)
print("  Qora shchup Pico GND da. To'xtatish: Ctrl+C")
print("=" * 58)

try:
    # ---------- 1. Doimiy YUQORI: simlar va bo'luvchi butunmi ----------
    statik(1)
    bosqich(1, "GP16 doimiy 3.3 V (tovush yo'q, faqat o'lchov)",
            ["GP16 (21-pin) ... kutilgan  3.3 V",
             "A nuqta       ... kutilgan  0.82 V   (3.3 x 3.3k / 13.3k)",
             "",
             "A da 0 V     -> R2 uzilgan yoki 36-sim ulanmagan",
             "A da 3.3 V   -> R3 ulanmagan (bo'luvchi yo'q)",
             "A da 0.3 V dan past -> C1 dan keyin qisqa tutashuv yoki NL yerga tushgan"])
    pauza()

    # ---------- 2. Doimiy PAST ----------
    statik(0)
    bosqich(2, "GP16 doimiy 0 V",
            ["GP16 ... kutilgan  0 V",
             "A     ... kutilgan  0 V",
             "",
             "Bu yerda 0 chiqmasa — A nuqtaga boshqa manba tegib turibdi"])
    pauza()

    # ---------- 3. Usilitel quvvati ----------
    bosqich(3, "Usilitel quvvati (Pico dan mustaqil)",
            ["USIL VCC - USIL GND (quvvat shtirlari) ... kutilgan  24 V",
             "AL-2402 chiqishi                        ... kutilgan  24 V",
             "",
             "24 V yo'q -> 34/35 simlar yoki blok pitaniya",
             "24 V bor, lekin plata sovuq/indikator yonmaydi -> usilitel nosoz"])
    pauza()

    # ---------- 4. 1 kHz, DC o'rtacha qiymat ----------
    tovush(1000, 50)
    bosqich(4, "1000 Hz, 50%  — DINAMIKDAN TOVUSH CHIQISHI KERAK",
            ["Multimetr DC rejimida:",
             "  GP16 ... kutilgan  ~1.65 V  (3.3 ning yarmi)",
             "  A     ... kutilgan  ~0.41 V",
             "",
             "Kuchlanish to'g'ri, tovush yo'q bo'lsa — ayb usilitel tomonda:",
             "  - tovush regulyatorini 50% ga buring",
             "  - 39-sim (USIL signal GND -> Pico GND) ulanganmi",
             "  - C1 qutbi: + uchi A tomonda",
             "  - dinamik SPL+/SPL- ga mahkam ulanganmi"])
    pauza()

    # ---------- 5. 100 Hz, AC o'lchov ----------
    tovush(100, 50)
    bosqich(5, "100 Hz, 50%  — arzon multimetr AC ni shu chastotada o'lchaydi",
            ["Multimetr AC (V~) rejimida:",
             "  A nuqta   ... kutilgan  0.3 ... 0.45 V",
             "  USIL NL   ... kutilgan  shunga yaqin (C1 dan keyin)",
             "",
             "A da signal bor, NL da yo'q -> C1 uzilgan yoki teskari/quritilgan",
             "Ikkalasida ham bor, tovush yo'q -> usilitel yoki dinamik"])
    pauza()

    # ---------- 6. Chastota supurgisi ----------
    bosqich(6, "200 -> 2000 Hz supurgi (10 s) — quloq bilan tekshirish",
            ["Ohang ko'tarilib borishi kerak. Shitirlash ham signal bor degani."])
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 10000:
        f = 200 + (time.ticks_diff(time.ticks_ms(), t0) * 180) // 1000
        tovush(f, 50)
        time.sleep_ms(20)
    tovush(1000, 50)
    pauza()

    # ---------- 7. Baland signal ----------
    tovush(1000, 90)
    bosqich(7, "1000 Hz, 90%  — signal kuchaytirilgan",
            ["50% da eshitilmay, 90% da eshitilsa — daraja past.",
             "Yechim: R3 ni 3.3k dan 10k ga almashtiring (A dagi signal 2 barobar kattaroq)."])
    pauza()

    # ---------- 8. Rele va lampa ----------
    ochir()
    rele = Pin(GP_RELE, Pin.OUT, value=1)
    bosqich(8, "Rele (lampa) — 3 marta ulanadi",
            ["Rele 'chirt' etib ishlashi va lampa yonishi kerak."])
    for i in range(3):
        rele.value(0)
        time.sleep_ms(400)
        rele.value(1)
        time.sleep_ms(400)
    pauza()

    # ---------- 9. To'liq avariya taqlidi ----------
    bosqich(9, "AVARIYA taqlidi (10 s) — main.py dagi kabi",
            ["Lampa 1 s yonadi / 1 s o'chadi, tovush 800 va 1200 Hz orasida almashadi."])
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 10000:
        e = time.ticks_diff(time.ticks_ms(), t0)
        if (e // 1000) % 2 == 0:
            rele.value(0)
            tovush(800 if (e // 250) % 2 == 0 else 1200, 50)
        else:
            rele.value(1)
            ochir()
        time.sleep_ms(5)

    ochir()
    rele.value(1)
    print("")
    print("  Sinov tugadi. Qaysi bosqichda kutilgan qiymat chiqmadi — ayb shu yerda.")
    print("")

except KeyboardInterrupt:
    pass
finally:
    try:
        ochir()
        Pin(GP_RELE, Pin.OUT, value=1)
    except Exception:
        pass
