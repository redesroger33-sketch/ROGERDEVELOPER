"""Transcribe el audio por enunciados delimitados por pausas reales."""
import json, wave, sys
import numpy as np
import sherpa_onnx

WAV = "_work/audio16k.wav"
MODEL = "sherpa-onnx-whisper-small"

def load():
    w = wave.open(WAV); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)/32768.0
    return sr, a

def pauses_of(a, sr):
    hop = int(sr*0.02)
    rms = np.array([np.sqrt((a[i:i+hop]**2).mean())+1e-9 for i in range(0, len(a)-hop, hop)])
    db = 20*np.log10(rms)
    sm = np.convolve(db, np.ones(5)/5, mode="same")
    lo, hi = np.percentile(sm,10), np.percentile(sm,90)
    voiced = sm > lo + 0.42*(hi-lo)
    out, i = [], 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]: j += 1
            if (j-i)*0.02 >= 0.18: out.append((i*0.02, j*0.02))
            i = j
        else: i += 1
    return out

def utterances(pauses, dur, min_gap=0.55, max_len=12.0, min_len=3.5):
    """Tramos de voz; corta solo en pausas >= min_gap o al superar max_len."""
    spans, cur = [], 0.0
    for ps, pe in pauses:
        if ps > cur: spans.append((cur, ps))
        cur = pe
    if cur < dur: spans.append((cur, dur))
    spans = [(s,e) for s,e in spans if e-s > 0.12]

    utts, cs, ce = [], None, None
    for k,(s,e) in enumerate(spans):
        if cs is None: cs, ce = s, e; continue
        gap = s - ce
        if gap >= min_gap or (e - cs) > max_len:
            utts.append((cs, ce)); cs, ce = s, e
        else:
            ce = e
    if cs is not None: utts.append((cs, ce))

    # fusiona enunciados demasiado cortos: sin contexto el ASR los destroza
    merged = []
    for s_, e_ in utts:
        if merged and (e_ - s_) < min_len and (e_ - merged[-1][0]) <= max_len + 4:
            merged[-1] = (merged[-1][0], e_)
        else:
            merged.append((s_, e_))
    return merged

def main():
    sr, a = load()
    dur = len(a)/sr
    utts = utterances(pauses_of(a, sr), dur)
    print(f"{len(utts)} enunciados detectados en {dur:.2f}s", flush=True)

    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{MODEL}/small-encoder.onnx",
        decoder=f"{MODEL}/small-decoder.onnx",
        tokens=f"{MODEL}/small-tokens.txt",
        language="es", task="transcribe", num_threads=4,
    )

    out = []
    for i,(s,e) in enumerate(utts, 1):
        pad = 0.10
        i0 = max(0, int((s-pad)*sr)); i1 = min(len(a), int((e+pad)*sr))
        st = rec.create_stream()
        st.accept_waveform(sr, a[i0:i1])
        rec.decode_stream(st)
        txt = st.result.text.strip()
        out.append({"start": round(s,2), "end": round(e,2), "text": txt})
        print(f"[{i:02d}] {s:6.2f}-{e:6.2f}  {txt}", flush=True)

    json.dump(out, open("utterances.json","w"), ensure_ascii=False, indent=1)
    print("TRANSCRIPCION_OK")

main()
