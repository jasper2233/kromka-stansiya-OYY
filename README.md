# Kromka stansiyasi

Kromka yopishtirish uskunasida detal uzunligini ikkita datchik bilan o'lchash, QR kod orqali MES bilan solishtirish, ogohlantirish.

## Tez boshlash

**Pico:**
1. BOOTSEL bosib turib USB ga ulang → `RPI-RP2` diski → MicroPython `.uf2` ni ko'chiring
2. Thonny → `pico/main.py` ni oching → File → Save as → Raspberry Pi Pico → `main.py`

**Server va stansiya:**
```
cd server
python mes_server.py
```
Brauzerda: `http://localhost:8000` (stansiya), `http://localhost:8000/tablo` (tablo).

**Diagnostika:** `pico/tekshir.py` — kirishlar holati (GP1/GP5/GP9/GP13). `pico/test_pico.py` — brauzersiz o'lchov. `pico/tovush_test.py` — tovush zanjiri, multimetr bilan bosqichma-bosqich.

## Hujjatlar

`docs/` papkasida, brauzerda oching va `Ctrl+P` bilan chop eting:

- `TZ_kromka_kontroller.html` — texnik topshiriq v1.2
- `yigish_sxemasi.html` — to'liq yig'ish sxemasi, 45 sim
- `onlayn_mes_yoriqnoma.html` — haqiqiy MES ga o'tish, Chrome kiosk, avtomatik sozlash

Loyiha konteksti Claude Code uchun: `CLAUDE.md`.
