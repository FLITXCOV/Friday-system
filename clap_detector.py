import vosk
import sounddevice as sd
import numpy as np
import json
import queue
import subprocess
import os
import sys
import time

# ─── Configuration ───────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
DEVICE_INDEX = 1  # Microphone Array (Realtek) - confirmed working

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
FRIDAY_URL = "http://localhost:5173"

# Grammar: constrain vosk to only listen for these words (dramatically improves accuracy)
GRAMMAR = '["neo matrix", "neo", "matrix", "no matrix", "new matrix", "[unk]"]'

# Fuzzy matching: accept any of these as the wake phrase
WAKE_WORDS_NEO = {"neo", "no", "new", "neil", "nio", "nio"}
WAKE_WORDS_MATRIX = {"matrix", "mattress", "matrices"}

# ─── Globals ─────────────────────────────────────────────────────────────────
audio_queue = queue.Queue()
cooldown_until = 0  # timestamp until which we ignore wake phrases


def is_wake_phrase(text):
    """Check if the recognized text is close enough to 'neo matrix'."""
    words = text.lower().split()
    has_neo = any(w in WAKE_WORDS_NEO for w in words)
    has_matrix = any(w in WAKE_WORDS_MATRIX for w in words)
    return has_neo and has_matrix


def launch_friday():
    """Open F.R.I.D.A.Y. UI visibly using PowerShell Start-Process."""
    global cooldown_until
    print('WAKE PHRASE "NEO MATRIX" DETECTED!')
    print("Opening F.R.I.D.A.Y. UI...")

    ps_command = (
        f'Start-Process -FilePath "{CHROME_PATH}" '
        f'-ArgumentList "--app={FRIDAY_URL}",'
        f'"--autoplay-policy=no-user-gesture-required",'
        f'"--use-fake-ui-for-media-stream" '
        f'-WindowStyle Maximized'
    )
    subprocess.Popen(
        ["powershell", "-Command", ps_command],
        creationflags=0x08000000  # CREATE_NO_WINDOW for powershell itself
    )

    # 60-second cooldown to prevent duplicate windows
    cooldown_until = time.time() + 60
    print("F.R.I.D.A.Y. launched! Pausing wake word detection for 60 seconds...")


def audio_callback(indata, frames, time_info, status):
    """Called by sounddevice for each audio block."""
    if status:
        print(f"  [audio: {status}]", file=sys.stderr)
    audio_queue.put(bytes(indata))


def main():
    global cooldown_until

    print("Loading offline speech recognition model...")
    model = vosk.Model(model_name="vosk-model-small-en-us-0.15")
    # Use grammar-constrained recognizer for much better wake word accuracy
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)

    print('Wake word detector online — say "NEO MATRIX" to summon F.R.I.D.A.Y.')

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=4000,
        dtype="int16",
        channels=1,
        device=DEVICE_INDEX,
        callback=audio_callback,
    ):
        while True:
            data = audio_queue.get()

            # Skip processing during cooldown
            if time.time() < cooldown_until:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text and text != "[unk]":
                    print(f"  Heard: [{text}]")
                    if is_wake_phrase(text):
                        launch_friday()
            else:
                partial = json.loads(recognizer.PartialResult())
                text = partial.get("partial", "").strip()
                if text and text != "[unk]" and is_wake_phrase(text):
                    launch_friday()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Wake word detector stopped.")

