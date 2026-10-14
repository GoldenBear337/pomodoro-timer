"""End-of-session chime, generated once as a WAV in the app folder (no bundled assets)."""
import math
import os
import struct
import wave
import winsound

RATE = 22050


def _tone(freq, secs, volume=0.35):
    frames = []
    n = int(RATE * secs)
    for i in range(n):
        t = i / RATE
        envelope = math.exp(-4.0 * t)  # soft bell-like decay
        sample = volume * envelope * (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t))
        frames.append(struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 32767)))
    return b"".join(frames)


def ensure_chime(folder):
    path = os.path.join(folder, "chime.wav")
    if not os.path.exists(path):
        data = _tone(880, 0.35) + _tone(1318.5, 0.9)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(data)
    return path


def play(path):
    try:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except RuntimeError:
        winsound.MessageBeep()
