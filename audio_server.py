import io
import os
import socket
import threading
import pygame
import mutagen.mp3
from pydub import AudioSegment
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')

VALID_LANGS = {
    'it-IT', 'en-GB', 'fr-FR', 'de-DE', 'es-ES', 'pt-PT',
    'ru-RU', 'zh-CN', 'ja-JP', 'ko-KR', 'ar-SA', 'nl-NL', 'he-IL',
    'pl-PL', 'hr-HR', 'vi-VN', 'el-GR', 'tr-TR'
}

VOLUME_BOOST_DB = 1.58  # +20% ampiezza

pygame.mixer.init()
_lock = threading.Lock()


@app.route('/')
@app.route('/biba-boutique.html')
def boutique():
    return send_from_directory(BASE_DIR, 'biba-boutique.html')


@app.route('/audio/<path:filename>')
def audio_file(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/<path:filename>')
def static_file(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route('/play/<lang>')
def play_on_laptop(lang):
    if lang not in VALID_LANGS:
        return jsonify({'error': 'lingua non valida'}), 400

    path = os.path.join(AUDIO_DIR, f'{lang}.mp3')
    if not os.path.exists(path):
        return jsonify({'error': 'file non trovato'}), 404

    def _play():
        with _lock:
            audio = AudioSegment.from_mp3(path) + VOLUME_BOOST_DB
            buf = io.BytesIO()
            audio.export(buf, format='wav')
            buf.seek(0)
            pygame.mixer.music.stop()
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play()

    threading.Thread(target=_play, daemon=True).start()

    try:
        duration = mutagen.mp3.MP3(path).info.length
    except Exception:
        duration = 14

    return jsonify({'ok': True, 'lang': lang, 'duration': round(duration, 1)})


if __name__ == '__main__':
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = '127.0.0.1'

    print()
    print('=' * 50)
    print('  BIBA BOUTIQUE - Audio Server')
    print('=' * 50)
    print(f'  Apri sul tablet:  http://{local_ip}:5000')
    print(f'  Oppure:           http://localhost:5000')
    print()
    print('  Premi Ctrl+C per fermare')
    print('=' * 50)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
