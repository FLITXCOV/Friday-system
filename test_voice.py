"""Test the final wake word detection with grammar + fuzzy matching."""
import vosk
import sounddevice as sd
import json
import queue
import time

SAMPLE_RATE = 16000
DEVICE_INDEX = 1
GRAMMAR = '["neo matrix", "neo", "matrix", "no matrix", "new matrix", "[unk]"]'

WAKE_WORDS_NEO = {"neo", "no", "new", "neil", "nio"}
WAKE_WORDS_MATRIX = {"matrix", "mattress", "matrices"}

audio_queue = queue.Queue()

def callback(indata, frames, time_info, status):
    audio_queue.put(bytes(indata))

def is_wake_phrase(text):
    words = text.lower().split()
    has_neo = any(w in WAKE_WORDS_NEO for w in words)
    has_matrix = any(w in WAKE_WORDS_MATRIX for w in words)
    return has_neo and has_matrix

print("=" * 50)
print("  Wake Word Test — Say 'NEO MATRIX'")
print("=" * 50)
print()
print("Loading model...")
model = vosk.Model(model_name="vosk-model-small-en-us-0.15")
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)
print("LISTENING — Say 'NEO MATRIX' now...")
print()

start = time.time()
matched = False
with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype="int16",
                       channels=1, device=DEVICE_INDEX, callback=callback):
    while time.time() - start < 30 and not matched:
        data = audio_queue.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if text and text != "[unk]":
                print(f"  >> Heard: [{text}]")
                if is_wake_phrase(text):
                    print()
                    print("  *** MATCHED! F.R.I.D.A.Y. would launch now! ***")
                    matched = True
        else:
            partial = json.loads(rec.PartialResult())
            p = partial.get("partial", "").strip()
            if p and p != "[unk]":
                if is_wake_phrase(p):
                    print(f"  >> Heard: [{p}]")
                    print()
                    print("  *** MATCHED! F.R.I.D.A.Y. would launch now! ***")
                    matched = True
                else:
                    print(f"  ... hearing: [{p}]          ", end="\r")

if not matched:
    print("\nNo match in 30 seconds.")
input("\nPress Enter to close...")
