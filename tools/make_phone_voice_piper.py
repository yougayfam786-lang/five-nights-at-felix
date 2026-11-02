#!/usr/bin/env python3
"""Records the phone guy's lines with Piper (free, runs offline) and builds them into index.html.

Usage, from the felix-game folder:
    tools/.piper-venv/bin/python tools/make_phone_voice_piper.py           # only lines not recorded yet
    tools/.piper-venv/bin/python tools/make_phone_voice_piper.py --force   # re-record everything

Voice: "ryan" (medium) from https://huggingface.co/rhasspy/piper-voices, kept in tools/piper-voice.
The text comes from the CALLS block in index.html, so edit the lines there.
"""
import pathlib
import subprocess
import sys
import wave

from piper import PiperVoice, SynthesisConfig

from make_phone_voice import GAME, OUT, build_into_game, read_lines

MODEL = pathlib.Path(__file__).resolve().parent / 'piper-voice' / 'en_US-ryan-medium.onnx'
# nights 1-3: a bit slower and steadier; night 4: rushed and shaky
CALM = SynthesisConfig(length_scale=1.08, noise_scale=0.7, noise_w_scale=0.85)
PANIC = SynthesisConfig(length_scale=0.92, noise_scale=0.9, noise_w_scale=1.0)


def main():
    force = '--force' in sys.argv
    voice = PiperVoice.load(str(MODEL))
    OUT.mkdir(parents=True, exist_ok=True)
    clips = {}
    for night, lines in sorted(read_lines(GAME.read_text(encoding='utf-8')).items()):
        for i, text in enumerate(lines):
            name = f'call{night}_{i}'
            m4a = OUT / f'{name}.m4a'
            if force or not m4a.exists():
                print(f'recording {name}: {text[:60]}')
                wav = OUT / f'{name}.wav'
                with wave.open(str(wav), 'wb') as w:
                    voice.synthesize_wav(text, w, syn_config=PANIC if night >= 4 else CALM)
                subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav), str(m4a)], check=True)
                wav.unlink()
            clips[name] = m4a.read_bytes()
    build_into_game(clips, 'audio/mp4')


if __name__ == '__main__':
    main()
