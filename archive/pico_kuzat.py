import serial, time, subprocess
from serial.tools import list_ports
def bor():
    return [p.device for p in list_ports.comports() if p.vid == 0x2E8A]
def t(): return time.strftime('%H:%M:%S')
t0 = time.time()
print(t(), 'Pico kutilyapti...', flush=True)
while not bor() and time.time() - t0 < 600: time.sleep(0.3)
if not bor(): print('10 daqiqada ulanmadi'); raise SystemExit
port = bor()[0]; print(t(), 'ulandi:', port, flush=True)
time.sleep(1.5)
s = None
for i in range(10):
    try: s = serial.Serial(port, 115200, timeout=0.2); break
    except Exception as e: print(t(), 'ochilmadi:', e, flush=True); time.sleep(1)
if s:
    s.write(b'HOLAT\n'); oxirgi = time.time(); ping = 0; tm = time.time()
    while time.time() - tm < 180:
        if time.time() - ping > 2:
            try: s.write(b'HB\nPING\n')
            except Exception as e: print(t(), 'YOZISH XATO:', e, flush=True); break
            ping = time.time()
        try: q = s.readline()
        except Exception as e: print(t(), 'OQISH XATO:', e, flush=True); break
        if q:
            oxirgi = time.time(); x = q.decode(errors='replace').strip()
            if '"pong"' not in x: print(t(), '<<', x[:300], flush=True)
            else: pong = x
        if time.time() - oxirgi > 5: print(t(), 'JIM', int(time.time()-oxirgi), 's', 'port bor' if bor() else 'PORT YOQ', flush=True); time.sleep(1)
    print(t(), 'oxirgi pong:', pong if 'pong' in dir() else '-', flush=True)
    s.close()
print(t(), 'kiosk ochilyapti', flush=True)
subprocess.Popen(['cmd', '/c', r'D:\kromka stansiya OYY\server\kiosk_ishga_tushirish.bat'], cwd=r'D:\kromka stansiya OYY\server')
