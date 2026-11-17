"""Pista instrumental original (sin derechos de terceros): piano/pad cálido + beat suave, ~92 bpm."""
import sys, wave
import numpy as np

SR = 44100
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
out = sys.argv[1]
bpm = 92
beat = 60 / bpm
n = int(SR * dur)
mix = np.zeros(n)
t_all = np.arange(n) / SR

def note(freq, start, length, amp, kind="piano"):
    s = int(start * SR); e = min(n, s + int(length * SR))
    if s >= n: return
    t = np.arange(e - s) / SR
    if kind == "piano":
        w = sum(np.sin(2*np.pi*freq*k*t) * (0.6**(k-1)) for k in range(1, 5))
        env = np.exp(-3.2*t) * np.minimum(1, t/0.005)
    elif kind == "pad":
        w = np.sin(2*np.pi*freq*t) + 0.5*np.sin(2*np.pi*freq*1.003*t) + 0.3*np.sin(2*np.pi*freq*2*t)
        env = np.minimum(1, t/0.6) * np.minimum(1, (length - t)/0.6)
    else:  # bass
        w = np.sin(2*np.pi*freq*t) + 0.2*np.sin(2*np.pi*freq*2*t)
        env = np.exp(-2.0*t) * np.minimum(1, t/0.01)
    mix[s:e] += amp * w * env

def hz(m): return 440 * 2 ** ((m - 69) / 12)

# Progresión I–V–vi–IV en Do mayor (cálida, positiva)
chords = [[60, 64, 67, 71], [55, 59, 62, 67], [57, 60, 64, 67], [53, 57, 60, 64]]
bass = [36, 31, 33, 29]
bar = beat * 4
rng = np.random.default_rng(7)
i = 0; t0 = 0.0
while t0 < dur:
    c = chords[i % 4]
    for m in c: note(hz(m), t0, bar, 0.035, "pad")
    note(hz(bass[i % 4]), t0, beat*2, 0.22, "bass"); note(hz(bass[i % 4]), t0 + beat*2.5, beat*1.5, 0.16, "bass")
    # arpegio de piano en corcheas
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    for k, p in enumerate(pattern):
        note(hz(c[p] + 12), t0 + k*beat/2, beat*1.5, 0.07 + 0.02*rng.random(), "piano")
    # beat suave: kick en 1 y 3, hat en corcheas, clap en 2 y 4
    for b in range(4):
        st = t0 + b*beat
        s = int(st*SR); L = int(0.25*SR)
        if s < n:
            tt = np.arange(min(L, n-s))/SR
            if b in (0, 2):
                mix[s:s+len(tt)] += 0.35*np.sin(2*np.pi*(55+90*np.exp(-30*tt))*tt)*np.exp(-9*tt)
            else:
                mix[s:s+len(tt)] += 0.06*rng.standard_normal(len(tt))*np.exp(-25*tt)
        for h in (0, 0.5):
            s2 = int((st + h*beat)*SR); L2 = int(0.05*SR)
            if s2 < n:
                k2 = min(L2, n-s2); tt = np.arange(k2)/SR
                mix[s2:s2+k2] += 0.025*rng.standard_normal(k2)*np.exp(-80*tt)
    i += 1; t0 += bar

# eco suave + fade in/out + normalizar
d = int(0.27*SR); echo = np.zeros(n); echo[d:] = mix[:-d]*0.25
mix = mix + echo
fade = np.minimum(1, t_all/1.0) * np.minimum(1, (dur - t_all)/1.5)
mix *= fade
mix = mix / np.max(np.abs(mix)) * 0.85
pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("ok", out, dur)
