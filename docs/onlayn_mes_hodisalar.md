# Onlayn MES uchun: kromka stansiyasi hodisalari

Bu hujjat `mes.mebelix.uz` dasturchisi uchun. Kromka stansiyasi (Pico + brauzer)
MES ga `POST /api/events` orqali hodisa yuboradi. Quyida **yangi hodisa turlari**
va **skan bilan o'lchovni juftlash** qoidasi.

Har so'rov: `{"events":[ {...}, {...} ]}`, javob: `{"ack":["<id>", ...]}`.
Har hodisada `id` (takrorlanmas), `station`, `ts` (ISO, UTC) bo'ladi.
`ack` ga tushmagan hodisani stansiya qayta yuboradi — `id` bo'yicha dublikatni
tashlang.

---

## 1. YANGI: `tiqilish` — detallar tiqilib qolgan, o'lchov chiqarilmaydi

Proshivka v1.16 dan. Ilgari bunday holatda **soxta o'lcham** chiqardi
(masalan 594 mm o'rniga 1259.9 mm). Endi stansiya o'lchov o'rniga shu hodisani
yuboradi.

```json
{
  "id": "KROMKA-01-000123-mu9uvq8b",
  "station": "KROMKA-01",
  "ts": "2026-09-21T03:40:00.000Z",
  "type": "tiqilish",
  "sabab": "birga_otdi",
  "n": 2,
  "L2": 1100.0,
  "L1": [500.0, 600.0]
}
```

| Maydon | Ma'nosi |
|---|---|
| `sabab` | `birga_otdi` — bir necha detal bir-biriga tiqilib, ikkinchi datchikdan **birga** o'tgan. `vaqt_mos_emas` — D1 va D2 vaqtlari bitta detalga to'g'ri kelmadi (detal datchik ostida to'xtab qolgan) |
| `n` | O'lchanmay qolgan detallar soni |
| `L2` | Ikkinchi datchik ko'rgan umumiy uzunlik, mm |
| `L1` | Birinchi datchik bo'yicha shu detallarning uzunliklari, mm |

**Ko'rsatish:** jonli ro'yxatda qizil qator, o'lcham o'rniga matn. Masalan:
`2 ta detal birga o'tdi (D2 1100 mm, D1 bo'yicha 500 + 600)`.
Bu detallar **o'lchanmagan** — ularni "mos" ham, "mos emas" ham deb hisoblamang,
operator qayta o'tkazishi kerak.

## 2. `avariya_toxtash` — stanok yo'lda detal bor paytda to'xtadi

```json
{"type":"avariya_toxtash","d1":1,"d2":0,"oraliq":2,"birga":0}
```
`d1`/`d2` — detal o'sha datchikda turibdi; `oraliq` — datchiklar orasida nechta
detal qolgan; `birga` — uzun detal ikkala datchikda. Bu detallarning o'lchovi
**bekor qilinadi** (ular uchun `olchov` kelmaydi).

## 3. `pico` — kontroller ulangan/uzilgan

```json
{"type":"pico","holat":0}
```
`holat: 1` — stansiya Pico ni topdi; `0` — uzildi. Stanok ishlamayotganini
shu bilan bilasiz.

## 4. `xotiradan: 1` — keyin yetkazilgan yozuv

Stansiya (kompyuter/brauzer) o'chiq bo'lsa, Pico o'lchovlarni o'z xotirasida
saqlaydi (300 tagacha) va aloqa tiklanganda yuboradi. Bunday hodisada
`"xotiradan": 1` bo'ladi, `ts` esa **hodisa haqiqatda bo'lgan vaqt** (stansiya
uni Pico bergan "necha ms oldin" qiymatidan hisoblaydi). Ya'ni `ts` kelib
tushgan vaqtdan ancha oldin bo'lishi mumkin — jadvalda `ts` bo'yicha
joylashtiring.

---

## 5. MUHIM: skan bilan o'lchovni juftlash

### Hozirgi muammo

2026-09-21, soat 08:54–08:59 da MES da har detal uchun **ikki yozuv** chiqqan:
biri noto'g'ri ("Mos emas"), keyingisi to'g'ri ("Mos"). Misollar:

| Vaqt | O'lchangan | Kutilgan | Natija |
|---|---|---|---|
| 08:54:38 | 289.0 | 700 (10_002) | Mos emas |
| 08:54:45 | 699.6 | 700 (10_002) | Mos |
| 08:57:27 | 272.3 | 1168 (12_010) | Mos emas |
| 08:57:36 | 1169.0 | 1168 (12_010) | Mos |
| 08:58:17 | 2212.9 | 668 (04_004) | Mos emas |
| 08:58:24 | 665.9 | 668 (04_004) | Mos |

Sabab — **vaqt siljishi**. Detal birinchi datchikdan ikkinchisiga yetib borishi
~15 soniya (2553 mm, 10 m/min), 18 m/min da ~8.4 s. Operator esa QR kodlarni
4–10 soniyada bir marta skanerlaydi (loglardan ko'rinadi: 08:54:27, 08:54:31,
08:54:37). Shu sababli **hozir kelayotgan o'lchov — 2–4 ta skan oldin
o'tkazilgan detalniki**. MES esa uni **oxirgi skan** bilan solishtiryapti.

### Yechim

Stansiya endi har o'lchovda **detal birinchi datchikka kirgan lahzani** ham
yuboradi:

```json
{
  "type": "olchov",
  "ts": "2026-09-21T03:54:45.000Z",     // o'lchov tayyor bo'lgan lahza (D2 dan chiqdi)
  "kirish_ts": "2026-09-21T03:54:29.400Z", // detal D1 ga kirgan lahza  ← YANGI
  "measured_mm": 699.6,
  "ish_ms": 15092.0,                     // D1 dan D2 gacha, ms
  "L1": 698.9, "L2": 700.3,
  "pico_kod": "OK",
  "v_meas": 10.15, "v_nom": 10,
  "verdict": "SKANERSIZ"                 // skaner MES agentida bo'lsa — doim shunday
}
```

Tavsiya etilgan juftlash algoritmi (server tomonda):

1. Har ish markazi uchun **skanlar navbatini** saqlang (FIFO): vaqti, QR, detal
   o'lchamlari (uzun/kalta), nechta tomon kerak.
2. O'lchov kelganda `kirish_ts` ga eng yaqin, **hali to'ldirilmagan** skanni
   oling. Oyna: `kirish_ts ± 20 s`.
3. Oynada bir nechta nomzod bo'lsa — **o'lchamga qarab** tanlang: `measured_mm`
   skanning uzun yoki kalta tomoniga dopusk ichida (masalan ±3 mm) mos kelsa,
   o'sha skan. Bu 289 mm ni 700 mm lik detalga yozib qo'yishdan saqlaydi.
4. Hech bir skan mos kelmasa — yozuvni "skanersiz / noma'lum" deb qo'ying, lekin
   **"Mos emas" (brak) deb belgilamang**: bu ko'pincha juftlash xatosi, detal
   nuqsoni emas.
5. `kirish_ts` bo'lmasa (eski stansiya), uni `ts − ish_ms` dan hisoblash mumkin.

Shu qoidadan keyin yuqoridagi "ikki yozuv" muammosi yo'qoladi: har detal bitta
skanga yopishadi, ortiqcha o'lchovlar esa o'z skanini topadi.

---

## 6. Stansiya yuboradigan barcha turlar

| `type` | Qachon |
|---|---|
| `olchov` | Detal ikkala datchikdan o'tdi (yoki bittasidan — `pico_kod` da `FAQAT1/FAQAT2`) |
| `tiqilish` | Detallar tiqilgan, o'lchov ishonchsiz — **yangi** |
| `avariya_toxtash` | Stanok yo'lda detal bor paytda to'xtadi |
| `ogoh` | Datchik nosozligi: `javob_yoq`, `yopishib_qolgan`, `iflos`, `tezlik_nomuvofiq` |
| `uskuna` | Stanok ishlayapti/to'xtadi (`holat` 1/0) |
| `tezlik` | 10 yoki 18 m/min rejimi |
| `pico` | Kontroller ulandi/uzildi |

`olchov` dagi `pico_kod`:
`OK` — ikkala datchik mos; `FARQ` — datchiklar farqi katta (linza iflos bo'lishi
mumkin); `FAQAT1`/`FAQAT2` — faqat bitta datchik ko'rgan.
