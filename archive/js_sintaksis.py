# -*- coding: utf-8 -*-
# stansiya.html dagi <script> bloklarini qavslar muvozanati bo'yicha qo'pol
# tekshirish (node yo'q, brauzersiz). Satr/shablon/izohlarni hisobga oladi.
import re, sys

p = r'D:\kromka stansiya OYY\server\stansiya.html'
src = open(p, encoding='utf-8').read()
bloklar = re.findall(r'<script[^>]*>(.*?)</script>', src, re.S)
print('script bloklari:', len(bloklar))

JUFT = {')': '(', ']': '[', '}': '{'}
xato = 0
for bi, kod in enumerate(bloklar):
    stack, i, n = [], 0, len(kod)
    satr = 1
    while i < n:
        c = kod[i]
        if c == '\n':
            satr += 1; i += 1; continue
        if c == '/' and i + 1 < n and kod[i+1] == '/':
            while i < n and kod[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and kod[i+1] == '*':
            j = kod.find('*/', i + 2)
            satr += kod.count('\n', i, j if j > 0 else n)
            i = (j + 2) if j > 0 else n
            continue
        # regex literali: / dan oldingi bo'sh bo'lmagan belgi operator bo'lsa
        if c == '/':
            oldingi = ''
            k = i - 1
            while k >= 0 and kod[k] in ' \t\n':
                k -= 1
            if k >= 0:
                oldingi = kod[k]
            if oldingi in '(,=:[!&|?{;+-*%~^<>' or oldingi == '':
                i += 1
                while i < n:
                    if kod[i] == '\\':
                        i += 2; continue
                    if kod[i] == '[':          # sinf ichida / oddiy belgi
                        while i < n and kod[i] != ']':
                            if kod[i] == '\\':
                                i += 1
                            i += 1
                    elif kod[i] == '/':
                        break
                    elif kod[i] == '\n':
                        break
                    i += 1
                i += 1
                continue
        if c in '"\'`':
            q, i = c, i + 1
            while i < n:
                if kod[i] == '\\':
                    i += 2; continue
                if kod[i] == '\n':
                    satr += 1
                if kod[i] == q:
                    break
                i += 1
            i += 1
            continue
        if c in '([{':
            stack.append((c, satr))
        elif c in ')]}':
            if not stack or stack[-1][0] != JUFT[c]:
                print('  XATO blok %d, satr %d: kutilmagan %s' % (bi, satr, c))
                xato += 1
                break
            stack.pop()
        i += 1
    if stack:
        print('  XATO blok %d: yopilmagan %s (satr %d)' % (bi, stack[-1][0], stack[-1][1]))
        xato += 1

for nom in ('function onSig', 'function tovush', 'function tovushOchir', "case 'sig'", 'acOch'):
    print(('  bor  ' if nom in src else '  YO\'Q ') + nom)

print('NATIJA:', 'muvozanat to\'g\'ri' if xato == 0 else '%d xato' % xato)
sys.exit(1 if xato else 0)
