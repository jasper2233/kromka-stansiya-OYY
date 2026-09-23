# -*- coding: utf-8 -*-
# v1.20 ni jonli tekshirish: versiya, kalibrlash, QR va TEST signallarida
# "sig" hodisalari kelyaptimi (MES ovozni shundan chaladi).
import json, time, serial

s = serial.Serial('COM6', 115200, timeout=0.3)
time.sleep(0.5)
s.reset_input_buffer()


def yubor(cmd, kut=2.0):
    s.write((cmd + '\n').encode())
    t0 = time.time()
    javob = []
    while time.time() - t0 < kut:
        l = s.readline()
        if l:
            javob.append(l.decode('utf-8', 'replace').strip())
    return [x for x in javob if x.startswith('{')]


print('--- HOLAT ---')
for x in yubor('HOLAT'):
    print(' ', x)
print('--- QR (lampa 2 marta miltillaydi, ovoz Pico da yo\'q) ---')
for x in yubor('QR', 1.5):
    print(' ', x)
print('--- TEST (lampa 1 s) ---')
for x in yubor('TEST', 2.0):
    print(' ', x)
s.close()
