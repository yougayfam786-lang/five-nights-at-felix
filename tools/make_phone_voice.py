#!/usr/bin/env python3
"""Records the phone guy's lines with ElevenLabs and builds them into index.html.

Usage (in a terminal, from the felix-game folder):
    ELEVENLABS_API_KEY=your_key python3 tools/make_phone_voice.py            # default voice
    ELEVENLABS_API_KEY=your_key python3 tools/make_phone_voice.py VOICE_ID   # any voice from your ElevenLabs library
    ... --force   re-record lines that already exist

Lines already saved in voices/phone are reused, so running it again costs no extra credits.
The text comes from the CALLS block in index.html, so edit the lines there.
"""
import base64
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME = ROOT / 'index.html'
OUT = ROOT / 'voices' / 'phone'
MODEL = 'eleven_multilingual_v2'
DEFAULT_VOICE = 'JBFqnCBsd6RMkjVDRZzb'  # "George", one of ElevenLabs' built-in voices

# nights 1-3: tired, a bit nervous; night 4: falling apart
CALM = {'stability': 0.4, 'similarity_boost': 0.8, 'style': 0.35, 'use_speaker_boost': True}
PANIC = {'stability': 0.2, 'similarity_boost': 0.8, 'style': 0.65, 'use_speaker_boost': True}


def read_lines(html):
    block = html[html.index('const CALLS = {'):]
    block = block[:block.index('\n};')]
    calls = {}
    for night, body in re.findall(r'(\d+):\s*\[(.*?)\]', block, re.S):
        calls[int(night)] = [json.loads('"' + m + '"') for m in re.findall(r'"((?:[^"\\]|\\.)*)"', body)]
    return calls


def record(key, voice, text, settings):
    req = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_64',
        data=json.dumps({'text': text, 'model_id': MODEL, 'voice_settings': settings}).encode(),
        headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f'ElevenLabs said no ({e.code}): {e.read().decode(errors="replace")[:400]}')


def main():
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        sys.exit('Set ELEVENLABS_API_KEY first, e.g.  ELEVENLABS_API_KEY=your_key python3 tools/make_phone_voice.py')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    voice, force = (args[0] if args else DEFAULT_VOICE), '--force' in sys.argv
    html = GAME.read_text(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)

    clips = {}
    for night, lines in sorted(read_lines(html).items()):
        for i, text in enumerate(lines):
            name = f'call{night}_{i}'
            path = OUT / f'{name}.mp3'
            if force or not path.exists():
                print(f'recording {name}: {text[:60]}')
                path.write_bytes(record(key, voice, text, PANIC if night >= 4 else CALM))
            clips[name] = path.read_bytes()

    build_into_game(clips, 'audio/mpeg')


def build_into_game(clips, mime):
    """Replaces the PHONE_SRC block in index.html with the given {name: audio bytes}."""
    html = GAME.read_text(encoding='utf-8')
    entries = ',\n'.join(f"  {k}: 'data:{mime};base64,{base64.b64encode(v).decode()}'" for k, v in clips.items())
    start, end = html.index('/*PHONE*/') + len('/*PHONE*/'), html.index('/*END*/')
    GAME.write_text(html[:start] + '{\n' + entries + '\n}' + html[end:], encoding='utf-8')
    print(f'done: {len(clips)} lines built into {GAME.name}')


if __name__ == '__main__':
    main()
