# Kromka stansiyasi — loyiha konteksti

Bu fayl Claude Code uchun. Loyiha tili — **o'zbek** (kod izohlari, UI, hujjatlar). Javoblarni o'zbek tilida bering.

## Nima bu

Mebel kromka yopishtirish uskunasidan o'tayotgan detalning uzunligini ikkita fotoelektrik datchik bilan o'lchab, QR kod orqali MES dagi kutilgan o'lcham bilan solishtiradigan tizim. Nomuvofiqlik yoki datchik nosozligida sirena va lampa bilan ogohlantiradi.

Foydalanuvchi — muhandis, elektronika bilan tanish lekin dasturchi emas. Tushuntirishlar aniq, misollar bilan.

## Arxitektura

```
[Datchik D1] → PC817 → GP1 ┐
[Datchik D2] → PC817 → GP5 ├→ [Pico, MicroPython] ←USB→ [Chrome kiosk, stansiya.html] ←HTTPS→ [MES server]
[RUN 24V]    → PC817 → GP9 │        ↓ GP0 rele → lampa                                          ↓
[18 m/min]   → PC817 → GP13┘        ↓ GP16 PWM → XH-M564 usilitel → dinamik              [SQLite / tablo.html]
```

- **Pico** vaqtni mikrosekundda o'lchaydi, JSON yuboradi, buyruq qabul qiladi. Mantiq minimal.
- **Brauzer** (WebSerial) — Pico va MES orasidagi shlyuz. QR skaner klaviatura sifatida keladi. Kalibrlash hisobi shu yerda.
- **MES** — detal ro'yxati, sozlamalar, hodisalar. Sinov serveri `server/mes_server.py` (stdlib, SQLite).

## Joylashuv

- **Ishchi papka: `D:\kromka stansiya OYY`** (2026-09-17 dan). MES server va kiosk shu yerdan ishlaydi (`server\kiosk_ishga_tushirish.bat`). Eski `Downloads\Telegram Desktop\kromka-stansiya` endi ishlatilmaydi.
- GitHub (PRIVATE): https://github.com/jasper2233/kromka-stansiya-OYY — o'zgarishdan keyin `git add -A; git commit; git push`. `server/mes.db` (sinov MES bazasi) ham repoda — foydalanuvchi ruxsati bilan, dasturchilar real hodisalar ko'rinishini ko'rishi uchun.
- git va gh admin siz o'rnatilgan: `%LOCALAPPDATA%\Programs\MinGit\cmd`, `%LOCALAPPDATA%\Programs\gh\bin` (foydalanuvchi PATH da).

## Papkalar

| Papka | Nima |
|---|---|
| `pico/main.py` | Asosiy proshivka. Thonny orqali Pico ga `main.py` nomi bilan yoziladi |
| `pico/tekshir.py` | Kirishlarni jonli kuzatish (diagnostika) |
| `pico/test_pico.py` | Brauzersiz sinov — natijalar Thonny Shell da |
| `pico/tovush_test.py` | Tovush zanjiri diagnostikasi — GP16→A→NL, har bosqichda kutilgan kuchlanish |
| `pico/signal_test.py` | QR va avariya signallari vaqtini rele/PWM dan o'lchaydi |
| `pico/sinov_pc.py` | `main.py` mantiqini **kompyuterda** sinash (soxta machine/time, lenta modeli): `python pico/sinov_pc.py` — 28 ssenariy; `python pico/sinov_pc.py 300` — tasodifiy to'xtashlar bilan og'ir sinov |
| `server/mes_server.py` | Sinov MES. `python mes_server.py` → http://localhost:8000 |
| `server/kiosk_ishga_tushirish.bat` | Bir bosishda: MES serveri + Chrome kiosk. Avtoyuklash uchun yorlig'ini `shell:startup` ga qo'ying |
| `server/stansiya.html` | Operator ekrani. Serverdan beriladi (WebSerial uchun https/localhost shart) |
| `server/tablo.html` | MES ko'rinishi: o'lchovlar, ogohlar, detallar, QR kodlar |
| `docs/TZ_kromka_stansiyasi_v2.html` | **Amaldagi TZ (v2.0, 2026-09-21)** — proshivka v1.18 holati: navbat qoidalari, tiqilish, signallar, protokol, MES aloqasi, kompyuter sozlamalari. Eski `docs/TZ_kromka_kontroller.html` (v1.2) tarix uchun qoldi |
| `docs/` | Yig'ish sxemasi, montaj yo'riqnomalari — HTML, bosib chiqariladi |
| `docs/onlayn_mes_hodisalar.md` | Onlayn MES (mes.mebelix.uz) dasturchisi uchun: `tiqilish` va boshqa hodisalar, skan↔o'lchov juftlash qoidasi |
| `archive/` | Eski versiyalar, ishlatilmaydi |

## Apparat — haqiqiy montaj (TZ v1.2, 3-bo'lim)

**Band pinlar faqat shular — TZ dan chiqilmaydi.** Boshqa pinni kodda ishlatmang. Yangi rele yoki kirish qo'shilsa — avval foydalanuvchi bilan TZ yangilanadi, keyin kod. Amaldagi TZ: `docs/TZ_kromka_stansiyasi_v2.html`.

| GPIO | Pin | Vazifa | Faol |
|---|---|---|---|
| GP1 | 2 | Datchik 1 (kirish), E3Z-T61 NPN, PC817 orqali | past |
| GP5 | 7 | Datchik 2 (chiqish) | past |
| GP9 | 12 | RUN — uskuna ishlayapti = 10 m/min | past |
| GP13 | 17 | 18 m/min rejimi | past |
| GP0 | 1 | Rele moduli IN (Tongling) — lampa **NO** kontaktda. **Yagona rele** | **yuqori = tortadi** (2026-09-17 amalda aniqlandi; kodda `RELE_YOQ = 1`) |
| GP16 | 21 | PWM → R2 10k → A → R3 3.3k → GND; A → C1 10µF → usilitel NL | — |

- Blok pitaniya AL-2402 24 V 2 A: datchiklar + usilitel. **0 V Pico GND bilan umumiy.**
- Uskuna 24 V (tezlik, RUN): **faqat optopara 1–2 oyoqlarida, Pico ga tegmaydi** — galvanik ajratilgan.
- Rele: VBUS 5 V dan. Kondensatorlar: C1 10µ audio, C2 100µ VBUS, C3 100µ/50V 24 V.
- Har optopara: `+24V → 4.7kΩ → 1-oyoq`, `2-oyoq → datchik qora`, `4 → GP`, `3 → Pico GND`.

## Protokol Pico ↔ brauzer (USB CDC 115200, har qator JSON)

Pico → brauzer:
```
{"ev":"boot"} {"ev":"tezlik","v":18} {"ev":"uskuna","holat":1}
{"ev":"olchov","n":42,"L":2474.5,"kod":"OK|FARQ|FAQAT1|FAQAT2","shubha":0,"L1":..,"L2":..,"d1":µs,"d2":µs,"v_olch":17.96,"v_nom":18,"yangi":1,"ish_ms":6650,"farq":2.8,"navbat":3}
{"ev":"kalib","S":18,"t1":µs,"t2":µs,"dt":µs,"dtm":µs}   ← faqat KALIB 1 rejimida
{"ev":"ogoh","ch":2,"sabab":"javob_yoq|yopishib_qolgan|iflos|tezlik_nomuvofiq","q":0}
{"ev":"avariya_toxtash","d1":1,"d2":0,"oraliq":0,"birga":0}   ← v1.12: stanok yo'lda detal bor paytda to'xtadi
{"ev":"tiqilish","sabab":"birga_otdi|d2_tasdiqlamadi|vaqt_mos_emas","n":2,"L2":1100.0,"L1":[500.0,600.0]}   ← v1.16/v1.17: D1/D2 vaqtlari bir detalga to'g'ri kelmadi, o'lchov chiqarilmaydi
{"ev":"yigilgan","n":12,"yoqolgan":0}   ← v1.13: stansiya qayta gapirganda, keyin xotiradagi har yozuv + "eski_ms"
{"ev":"holat","alarm":1}
{"ev":"holat","ver":"1.9","alarm":0,"uskuna":0,"v_nom":10,"kalib":0,"n":0,"navbat":0,"D":..,"V10":..,"V18":..,"K1":..,"K2":..,"B1":..,"B2":..,"C":..,"TD":..,"AO":..}  ← HOLAT javobi
{"ev":"kal",...barcha KAL}  ← SET javobi   {"ev":"pong","up":ms}  ← PING javobi
```
Brauzer → Pico (matn + `\n`): `QR` `ALARM` `STOP` `TEST` `KALIB 1|0` `SET D=.. V10=.. V18=.. K1=.. K2=.. B1=.. B2=.. C=.. TD=.. AO=0|1 HQ=Hz HA=Hz AV=0|1` `HB` `PING` `HOLAT`

- `HB` — stansiya yurak urishi, har 1 s, javobsiz. Pico `XOST_MS`=3 s buyruq ko'rmasa — stansiya yo'q: `olchov/ogoh/avariya_toxtash/uskuna` RAM ga yig'iladi (300 tagacha), stansiya qayta gapirganda `yigilgan` + har yozuv `eski_ms` bilan chiqadi. Stansiya ularni signal bermasdan, `ts = hozir − eski_ms` va `xotiradan:1` bilan MES ga yozadi.
- `HQ`/`HA` — skaner va avariya ohangi (Hz), `AV` — avariya ovozi (0 = ovozsiz, lampa baribir miltillaydi; skaner ovoziga ta'sir qilmaydi).
- SET qiymatlari o'zgarsa Pico `kal.json` ga yozadi va yonganda o'qiydi — stansiyasiz yonsa ham oxirgi kalibrlash bilan o'lchaydi.

- `AO=1` — lampa/sirena chalinmaydi (sozlash paytida), hodisalar baribir yuboriladi.
- Pico dagi standart qiymatlar: `D=2555 TD=12 AO=0`. Stansiya ulanganda o'z sozlamasini `SET` bilan yuboradi — shuning uchun stansiya va MES dagi qiymatlar ustun.

Eski `SET K=..` ham qabul qilinadi — ikkala datchikka bir xil qiymat tushadi.

## O'lchash mantiqi

- Har datchik mustaqil: `t` = nur to'silgan vaqt (µs).
- **QAT'IY NAVBAT: D1 yozuvi D2 tasdiqlamaguncha yo'qolmaydi (v1.17, 2026-09-21 talabi).** Ilgari navbat boshidagi yozuv `d2_kutish_ms` (10 m/min da ~23 s) dan uzoq kutsa TASHLANARDI va FAQAT1 chiqardi. Detal D1 dan o'tib, D2 tasdiqlashidan oldin (2–6 s ichida) D1 ga yangi detal kirsa, shu tashlash navbatni bir qadam siljitardi — keyin kelgan har bir D2 o'lchovi BOSHQA detalning D1 yozuvi bilan juftlanardi (MES da 594 mm o'rniga 1259.9, 606 o'rniga 1390.1). Endi:
  - **Vaqt bo'yicha hech narsa tashlanmaydi.** Navbat faqat D2 tasdiqlaganda yoki `KUTUV_MAX`(12) oshganda qisqaradi. Uzoq kutish — faqat `ogoh javob_yoq` sababi (yozuv joyida qoladi).
  - D2 detalni o'tkazganda **uzunliklar solishtiriladi** (`_yaqin`: 25% yoki kamida 30 mm, kichik uzunlikdan): navbat boshi mos kelsa — juft; bir necha yozuv YIG'INDISI mos kelsa — detallar **birga o'tgan** (`tiqilish`/`birga_otdi`); navbat boshi mos kelmay, keyingi yozuv aniq mos kelsa — oldingisi D2 gacha yetmagan (`tiqilish`/`d2_tasdiqlamadi`, navbat tekislanadi); hech biri mos kelmasa — `tiqilish`/`vaqt_mos_emas` (navbat boshi olinadi, tartib buzilmaydi).
  - Soxta o'lcham hech qachon chiqarilmaydi: ishonchsiz holat `tiqilish` hodisasi bo'lib ketadi.
  - **Navbat sig'imi masofadan hisoblanadi (v1.19)**: `kutuv_sigimi() = D/MIN_DETAL + 4 ≈ 21` (eng kichik detal 150 mm). Ilgari 12 ta edi — 150 mm li detallar ketma-ket tiqilganda oraliqqa 17 tasi sig'adi, navbat to'lib eng eski yozuv **D2 tasdiqlamasdan** chiqib ketardi va navbat siljirdi. Uzun detallarda (1100+ mm) bu hech qachon bo'lmasdi — shuning uchun muammo faqat kalta detallarda ko'rinardi (2026-09-21 shikoyati: kalta detallarda "ortiqcha o'tish", uzunlarida yo'q).
  - **Juftlash chegarasi 3% yoki 30 mm** (v1.19; ilgari 25%): 650 va 800 mm detallar "bir xil" deb qabul qilinardi. Bitta detalning D1/D2 farqi eng ko'pi 6.4 mm.
  - Detal D1 dan o'tayotganda yoki yo'lda ekan **tezlik almashgan** bo'lsa (`TEZ['us']` yozuvdan keyin) — uzunlik solishtirilmaydi, navbat tartibiga ishoniladi.
  - **Fizik tekshiruv (v1.18)**: detal D1 dan D2 gacha lentadan tez yura olmaydi. `dt < D/(v_nom·1.2)` bo'lsa — navbat boshidagi yozuv bu detalniki emas: yozuv navbatda QOLADI, o'lchov faqat D2 bo'yicha chiqadi (FAQAT2) va navbat o'zi tekislanadi. Bu Pico qayta yuklanganda (yoki tok uzilganda) yo'lda qolgan detallar D1 yozuvisiz D2 ga kelishidan kelib chiqadi; detallar bir xil uzunlikda bo'lsa uzunlik tekshiruvi buni sezmaydi, faqat imkonsiz tezlik ko'rsatadi (2026-09-21 da jonli kuzatildi: 27 m/min, nominal 10).
  - Tezlik yo'lda almashgan bo'lsa (`r['S'] != tezlik_nom()`) solishtirish o'tkazilmaydi — navbat tartibiga ishoniladi.
  - Avariyali to'xtashda ilingan (`bekor`) detallar solishtirilmaydi — tartib bo'yicha jimgina chiqariladi.
  - **O'lchangan tezlik nominaldan 20% dan ko'p farq qilsa** (detal oraliqda tiqilib turgan — `dt` shishgan), uzunlik NOMINAL tezlik bilan hisoblanadi: detal datchik ostidan to'liq tezlikda o'tgan, `t1/t2` to'g'ri.
- **D1→D2 navbati (FIFO)** (v1.8 dan): D ≈ 2555 mm oraliqda bir vaqtda 5–6 ta detal bo'lishi mumkin. D1 tugatgan har detal `kutuv` navbatiga yoziladi, D2 tugatganda eng eskisi bilan juftlanadi (lenta — detallar quvib o'tmaydi). Navbat boshi D1 **orqa qirrasidan** `D/v·1.5 + 500 ms` dan uzoq kutsa (v1.10 gacha old qirradan hisoblanardi — L > ~1300 mm detal FAQAT1+FAQAT2 ga bo'linib ketardi) — D2 ko'rmagan (FAQAT1). Navbat 12 dan oshsa eng eskisi yakunlanadi.
- **Markazlar bo'yicha tezlik**: `dt_mid = dt + (t2 − t1)/2` — detal *markazi* D1 dan D2 gacha qancha yurgani. Old va orqa frontlarning kechikishi o'zaro qisqaradi, tezlik esa aynan detal o'tgan oraliqda o'lchanadi. `v = D_eff / (dt_mid − C)`. Nominal 10/18 — metama'lumot va zaxira (dt bo'lmasa).
- **Har datchikning o'z tuzatmasi** (v1.11): `L1 = v·(t1 − K1) − B1`, `L2 = v·(t2 − K2) − B2`. `B` — uzunlik siljishi, mm (nur kengligi); `K` — vaqt kechikishi, ms. 2026-09-17 o'lchovida D1−D2 farqi 10 m/min da 35 ms, 18 da 21 ms, lekin mm da ikkalasida ≈6 mm — ya'ni farq asosan `B`, `K` emas. Ilgari bitta umumiy `K` edi — u datchiklar orasidagi doimiy farqni yashirib, FARQ chegarasiga yuklardi.
- Ikkalasi bor va farq ≤ TD → o'rtacha (OK). Farq > TD → kichigi (FARQ), uzunroq bergani shubhali (iflos linza uzaytiradi). Bittasi → FAQAT1/2.
- **Kalibrlash** (brauzerda): chiziqli eng kichik kvadratlar. Model `t_i = (L + B_i)/v + k_i`, `dt_mid = D/v + C` → `L_ref·dt_mid = D·t_i − B_i·dt_mid − a_i + C·L_ref`. 1 uzunlik → faqat `D`; 2+ uzunlik → `D, B1, B2`; 2+ uzunlik va 2 tezlik → `+C`, `K1/K2` faqat qoldiqni ≥10% kamaytirsa. 1 uzunlikda `Qo'llash` o'chiq. Nuqtalar `localStorage` da saqlanadi; `#kal=[...]` bilan bir martalik import. Ustunlar normallashtiriladi — aks holda normal tenglamalar shartlanishi buziladi va yechim yo'qoladi. 3σ dan chetdagi nuqtalar tashlanadi. Fizik chegaralar: `|B| ≤ 30 mm`, `|K| ≤ 5 ms`, `|C| ≤ 10 ms` — oshsa soddaroq model. (Eski 4 parametrli `D,K1,K2,C` modeli 1 uzunlik × 2 tezlikda K1=+13, K2=−14 ms kabi bema'ni qiymat bergan edi.)
- **Tarqoqlik ajratiladi**: `σ_mustaqil` = std(L1−L2)/2 (datchik va front shovqini — o'rtachada √2 marta kamayadi), `σ_umumiy` = qolgani (tezlik tebranishi, etalon xatosi). Hukm 2σ (95%) bo'yicha.
- Aniqlik: xato uzunlikka **proporsional**, asosiy hissa tezlik tebranishidan. 0.1% tebranish 2750 mm da ≈ 2.75 mm, 0.02% da ≈ 0.5 mm beradi. Ya'ni ±0.5 mm faqat lenta tezligi barqaror bo'lsa mumkin — buni kalibrlash hisoboti o'zi ko'rsatadi (guruhlar jadvalidagi σ uzunlik bo'yicha o'sadimi). Yetmasa yechim dasturiy emas, apparat: privodga enkoder.

## Ogohlantirish

GP0 dagi bitta rele. Lampa va tovush **doim birga** — `signal(yon)` bitta chaqiriqda. Ohang bitta: `TON_HZ = 2500` (baland `tut`), chastota faqat bir marta o'rnatiladi — `freq()` qayta chaqirilsa chirsillaydi. 2026-09-17 foydalanuvchi talabi bilan o'zgardi (TZ 7-bo'lim hujjati hali eski):
- Ohanglar alohida (v1.13): skaner `HQ` (standart 2500 Hz), avariya `HA` (1500 Hz). **Avariya ovozi** `AV` — o'chirilsa avariyada faqat lampa, skaner ovozi baribir chaladi. Stansiyada sarlavhadagi "avariya ovozi" tugmasi va "Signal sinovi" paneli (ohangni eshitib tanlash, skaner sinovi — MES ga yozilmaydi).
- `QR`: **0.5 s ichida 2 ta tut-tut**, lampa birga: 125 bor — 125 jim — 125 bor — 125 jim (`QR_MS`). Ilgari 150/150/150, 1000 Hz.
- `TEST`: lampa + tovush 1 s.
- `AVARIYA`: 1 s ikkalasi yonadi (bir tekis ohang), 1 s ikkalasi o'chadi, `STOP` gacha. Ilgari yongan paytda 800/1200 Hz almashardi — foydalanuvchi `buzuq, lampaga mos emas` dedi.
- **Avariyali to'xtash** (v1.12): stanok (RUN va 18 kirishlari ikkalasi) 200 ms dan uzoq o'chsa va shu payt detal D1 da, D2 da yoki ular orasida (navbatda) bo'lsa — `avariya_toxtash` hodisasi + AVARIYA, shu detallar o'lchovi bekor. Bekor detal qayta yongach datchikdan chiqsa ham o'lchov/FAQAT chiqmaydi (navbatga `bekor` belgisi bilan kiradi, D2 da jim tashlanadi). Stanok o'chiq paytda: kutish/yopishib qolish hisoblanmaydi, datchik ochilsa — detal qo'lda olingan (navbatga kirmaydi), yangi to'silish — bekor (avariyasiz). Yo'lda detal yo'q bo'lsa — oddiy to'xtash, avariyasiz. Avariyani Pico o'zi boshlaydi (datchik nosozligi) yoki brauzer (`ALARM`, o'lcham nomuvofiq). `AO=1` bo'lsa avariya boshlanmaydi.
- `pico/signal_test.py` shularni rele va PWM holatidan o'lchab tekshiradi (2026-09-16 v1.9 da hammasi o'tdi).
- Rele va PWM holati eslab qolinadi: bir xil qiymat qayta yozilmaydi (5 ms lik siklda PWM chastotasini qayta o'rnatish tovushni g'ijirlatadi).
- Uskuna to'xtatilmaydi — faqat indikatsiya. E-Stop bu tizimning vazifasi emas.

## MES API (sinov serveri beradi, haqiqiy MES ham shu shaklda bo'lishi kerak)

- Har `olchov` da `kirish_ts` ham yuboriladi (v1.16 stansiyasi): detal D1 ga **kirgan** lahza = `ts − (ish_ms + d2/1000)`. O'lchov D2 dan chiqqanda tayyor bo'ladi — bu detal kirganidan ~15 s (10 m/min) keyin, operator esa 4–10 s da bir skanerlaydi. Shuning uchun **skan bilan o'lchovni `ts` bo'yicha juftlab bo'lmaydi** — `kirish_ts` kerak. Onlayn MES uchun to'liq qoida: `docs/onlayn_mes_hodisalar.md`.
- `GET /api/part?qr=A-1001` → `{code,name,L,W,need}` yoki 404
- `GET /api/olchovlar?tur=skaner|skanersiz&n=200` — skaner bilan / skanersiz o'tgan detallar (`verdict` SKANERSIZ bo'yicha)
- `GET /api/jurnal?soat=24&station=X` → `[{holat: ishladi|to'xtadi|o'chiq, dan, gacha}]` — `uskuna` va `pico` hodisalaridan. **Stanok o'chiq** = Pico uzildi (stansiya `pico:0` yuboradi, 10 s da topilmasa ham) YOKI stansiya `JIM_S`=180 s dan ko'p `/api/settings` so'ramadi (kompyuter/Chrome o'chiq) — server `stansiya` jadvalida oxirgi ko'rinishni saqlaydi va qaytganda o'sha oraliqqa `pico:0` (`manba:server`) yozadi. `/api/stats` da `stanok: ishlayapti|to'xtagan|o'chiq`.
- MES/internet o'chiq bo'lsa: stansiya hodisalarni IndexedDB navbatda saqlab, aloqa tiklanganda asl `ts` bilan yuboradi (2026-09-17 jonli sinov: 60 s server o'chiq — 4 o'lchov keyin yetib keldi).
- `GET /api/settings?station=X` → `{station,kal:{D,V10,V18,K1,K2,C,TD,AO},tol:{detal},updated}` (eski `K` ham o'qiladi)
- `POST /api/settings` → `{ok,updated}`
- `POST /api/events` `{events:[{id,station,ts,type,...}]}` → `{ack:[id...]}`. `id` bo'yicha dublikat tashlanadi.

Stansiya har 60 s `settings` ni so'raydi; `updated` o'zgarsa Pico ga `SET`. Hodisalar IndexedDB navbatda, faqat `ack` dan keyin o'chadi.

## Joriy holat (2026-09-20)

### 2026-09-20: "MES ga ma'lumot bormay qoldi" — sabab va yechim

Shikoyat: monoblokda tizim ochiq tursa ham Pico "yo'q" bo'lib qolardi, MES ga hech narsa bormasdi; USB ni sug'urib-ulagandan keyin qaytadan ishlardi.

Dalillar:
- Bugungi 21 ta o'lchovning **hammasi `xotiradan: 1`** — Pico ishlagan va o'lchagan, lekin stansiya u bilan gaplashmagan. Ma'lumot yo'qolmagan (RAM xotira ishladi).
- Windows jurnali (42/107-hodisa): **monoblok kuniga bir necha marta uyquga tushgan** (9:50, 11:57, 14:57, 17:34). Uyqudan keyin CDC porti tiklanmaydi.
- **USB selective suspend yoqilgan edi** — jim turgan port uyquga qo'yilardi.
- Kiosk **`shell:startup` da yo'q edi** — kompyuter qayta yonsa stansiya o'zi ochilmasdi.
- Stansiyada **jimlik nazorati yo'q edi**: Pico o'zidan davriy xabar yubormaydi, shuning uchun "port ochiq, lekin aloqa o'lgan" holati sezilmasdi (na xato, na `done`).

Qilingan ishlar:
- Windows: uyqu va gibernatsiya o'chirildi (`standby/hibernate-timeout-ac 0`), **USB selective suspend o'chirildi**, kiosk yorlig'i `shell:startup` ga qo'yildi.
- `stansiya.html`: **jimlik nazorati** — 6 s jim tursa `PING`, 4 s ichida javob bo'lmasa portni yopib qayta ulaydi. Uzilganda yorliqda "Pico jim — qayta ulanmoqda".
- `kiosk_ishga_tushirish.bat`: Chrome fon bayroqlari (occluded windows, IntensiveWakeUpThrottling, memory saver o'chirildi) — yorliq muzlatilmasin.
- Proshivka **v1.15**: stansiya jim bo'lsa USB ga **umuman yozilmaydi** (`yubor` va `chop` ikkalasi ham) — o'qilmayotgan portga yozish CDC buferini to'ldirib, `print()` da butun dasturni qotirishi mumkin edi. **Qorovul (WDT 8 s)** qo'shildi: birinchi marta stansiya gapirgandan keyin yoqiladi (Thonny/mpremote da yoqilmaydi), qotib qolsa Pico qayta yuklanadi va USB qayta ro'yxatdan o'tadi.

**Pico da v1.16 yozilgan (2026-09-20 19:47, COM6).** Kalibrlash `kal.json` da saqlanib qoldi: `D=2553.37 B1=-2.19 B2=-5.73 C=0.885 V10=10.151 V18=18.227`. 2026-09-21 ertalab jonli ishladi: o'lchovlar stansiyaga to'g'ridan-to'g'ri kelyapti, tungi 41 ta yozuv Pico xotirasidan olindi (`xotiradan:1`), avariya/tiqilish yo'q.

- Apparat yig'ilgan, Pico o'lchayapti, datchiklar ishlaydi, rele ishlaydi.
- **Usilitel ishlaydi** — tovush bor, avariya va QR signallari eshitiladi.
- Sinov MES + stansiya + tablo ishlagan. QR skaner sinalgan.
- **v1.19 Pico ga yozilgan (2026-09-21, `sinov_pc.py` 40/40 + tasodifiy 40/40): kalta detallar tuzatildi** — navbat sig'imi 150 mm bo'yicha (≈21 ta), juftlash chegarasi 3%, tezlik almashgani hisobga olinadi. Yangi sinovlar: S39 (16 ta 150 mm detal ketma-ket), S40 (aralash uzunliklar 650/800/1860/150/1100). Oldingi v1.18 (38/38). v1.17 ning qat'iy navbati + fizik tezlik tekshiruvi (yuqoriga qarang). v1.17: D1 yozuvi D2 tasdiqlamaguncha tashlanmaydi (vaqt bo'yicha umuman tashlanmaydi), navbat boshi o'tkazib yuborilmaydi, ishonchsiz holatlar `tiqilish` bo'lib chiqadi. Oldingi v1.16 (2026-09-20, 35/35): tiqilishda juftlashni uzunlik bo'yicha tekshirish, kutish muddati 5 karra uzun, tiqilganda nominal tezlik bilan hisoblash, `tiqilish` hodisasi. v1.15: jim portga yozmaslik + WDT. v1.14 (2026-09-17): rele mantiqi teskari (`RELE_YOQ=1`) — Low trigger deb yozilgan edi, lampa NO kontaktda ovozga teskari yonardi. v1.13: stansiyasiz xotiraga yig'ish (`HB`), `kal.json`, alohida ohang `HQ/HA`, avariya ovozsiz rejimi `AV`. `pico/sinov_pc.py` 32 ssenariy o'tdi. v1.12 (arxivda): avariyali to'xtash, yangi QR/avariya signallari, sikl `qadam()` funksiyasida (sinov uchun). v1.11 (arxivda): v1.10 + `B1/B2`. v1.10: uzun detal (L > D) navbat muddati tuzatildi. v1.9 (2026-09-16 yozildi, `PING`/`HOLAT`/`SET` va `signal_test.py` o'tdi). v1.9 = v1.8 − TZ dan tashqari narsalar: GP2/GP3 qo'shimcha relelari, LO/AV/RP olib tashlandi, QR va AVARIYA signallari TZ 7-bo'limga qaytarildi. FIFO navbat va AO qoldi.
- v1.8 boshqa joyda yozilgan, kompyuterda nusxasi yo'q edi — Pico dan o'qib `archive/main_pico_2026-09-16_v1.8.py` ga saqlangan. v1.3 — `archive/main_2026-09-09_v1.3.py`, v1.2 — `archive/main_pico_2026-09-09_v1.2.py`.
- `stansiya.html` v1.9 ga mos: sozlamalarda "Avariya signali" (AO), standart D=2555 TD=12, HOLAT dan versiya chipda. `mes.db` dagi KROMKA-01 sozlamasi ham shu qiymatlarda.
- Pico COM porti o'zgarib turadi (COM3 → COM5 → COM6), MicroPython 1.29.0 (2026-09-17 da 1.28.0 dan yangilandi, `main.py` saqlanib qoldi). Portni VID 2E8A bo'yicha toping: `Get-PnpDevice -PresentOnly | ? InstanceId -match 'VID_2E8A'`.
- **Pico ulangan paytda headless Chrome (`--screenshot`, `--dump-dom`) ishlatmang**: u Pico USB deskriptorlarini o'qishga urinadi va Windows CDC drayveri qotadi ("Присоединенное к системе устройство не работает", 2026-09-17 da ikki marta) — faqat kabelni qayta ulash yordam berdi (Disable-PnpDevice uchun admin yo'q). Sahifani sinash kerak bo'lsa — avval Pico ni uzing yoki bu sinovni Pico ga yozish/tekshirishdan keyin qiling.
- Kiosk port tanlash oynasi Bluetooth qurilmalarini ~10 s qidiradi — Pico ro'yxatda shundan keyin chiqadi.
- Port "Отказано в доступе" bersa — uni Chrome (stansiya yoki WebSerial ishlatadigan boshqa sahifa) ushlab turibdi. Chrome ni butunlay yoping.
- Stansiya **avtomat ishlaydi**: Pico ni VID (0x2E8A) bo'yicha tanlaydi, USB uzilib-ulansa o'zi tutadi, har 5 s da qayta urinadi. Port ruxsati bir marta beriladi va Chrome profilida saqlanadi.
- **Kalibrlash qo'llandi (2026-09-17 11:23)**: 61 o'tkazish, 6 uzunlik (300, 580, 900, 1500, 1999.5, 2740) × 10/18 m/min. `D=2553.37 B1=-2.19 B2=-5.73 C=0.885 K1=-0.001 K2=-0.002 V10=10.151 V18=18.227`, MES va Pico da. Qoldiq σ=0.73 mm (2σ ±1.46), guruh ichida σ 0.2–0.9 mm. Guruh xatolari ikkala tezlikda bir xil (580: −0.9, 1500: +0.8, 2740: −0.5) — bu etalon uzunliklari aniq emasligi (nominal yozilgan), tezlik emas. "980" deb yozilgan detal aslida 900 mm edi.
- D1−D2 farqi detaldan detalga o'zgaradi (−1.4 … +6.4 mm), bitta detalda takrorlanadi — detal geometriyasi (qirra to'g'ri emasligi), kalibrlab bo'lmaydi; o'rtacha olinadi. TD=12 yetarli.
- **Keyingi:** etalonlarni shtangensirkul bilan o'lchab aniq `L_ref` kiritish (xom nuqtalar kiosk `localStorage` da, qayta o'tkazish shart emas) → qayta hisob. `AO=1` hali yoqilgan — ish rejimida 0 ga qaytarish. Keyin onlayn MES (`docs/onlayn_mes_yoriqnoma.html`).
- **Ochiq:** `docs/` dagi sxemalar hali eski GP2/GP6 datchik pinlarini ko'rsatadi (haqiqiy montaj GP1/GP5).

## Ishlab chiqish asboblari

- Pico ga fayl yozish: `python -m mpremote connect COM6 cp pico/main.py :main.py` (port raqamini avval tekshiring; Thonny yoki Chrome ochiq bo'lsa portni band qiladi — avval yoping).
- Pico ni jonli sinash: `mpremote ... reset`, keyin pyserial bilan portga `PING`/`HOLAT`/`TEST`/`QR`/`ALARM` yuborish. Pico dagi faylni o'qish: `mpremote connect COM6 cp :main.py <nusxa>` (dasturni to'xtatadi — keyin `reset`).
- Brauzer kodini brauzersiz tekshirish: `chrome --headless=new --dump-dom` — sahifa nusxasiga belgi qo'yuvchi `<script>` qo'shib, funksiyalar aniqlanganini tekshirish. `--dump-dom` async ishga tushishni kutmaydi, shuni hisobga oling.
- `mpremote` va `pyserial` o'rnatilgan (faqat ishlab chiqish uchun; loyiha kodi ularga bog'liq emas).

## Qoidalar

- Pico kodi MicroPython, faqat stdlib. IRQ ichida faqat navbatga yozish.
- Brauzer kodi vanilla JS, tashqi kutubxona yo'q (tablo.html da faqat qrcodejs CDN).
- Server stdlib Python. Tashqi paket qo'shmaslik.
- Fayl nomlari va o'zgaruvchilar o'zbekcha (lotin). JSON kalitlari qisqa.
- Xavfsizlik: uskuna 0 V hech qachon Pico GND ga ulanmaydi. Pico oyoqlariga 5 V/24 V berilmaydi.
