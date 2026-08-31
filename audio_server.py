import os
import socket
import threading
import pygame
import mutagen.mp3
from pydub import AudioSegment
from flask import Flask, send_from_directory, jsonify, request
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

VOLUME_BOOST_DB = 4.75  # +73% ampiezza (+20% tre volte)
TMP_WAV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_boost.wav')

# Traccia audio del video dei foulard: stesso principio delle bandiere,
# il suono esce dalle casse del computer, non dal tablet.
SCARF_MP3 = os.path.join(AUDIO_DIR, 'scarf.mp3')
TMP_SCARF_WAV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_scarf_boost.wav')

pygame.mixer.init()
_lock = threading.Lock()


@app.route('/')
@app.route('/biba-boutique.html')
def boutique():
    return send_from_directory(BASE_DIR, 'biba-boutique.html')


@app.route('/audio/<path:filename>')
def audio_file(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/video')
def video_page():
    """Indirizzo corto per il tablet: niente trattini bassi da digitare."""
    return send_from_directory(BASE_DIR, 'scarf_player.html')


@app.route('/tablet')
def tablet_qr():
    """Pagina col QR da inquadrare per aprire il video sul tablet."""
    return send_from_directory(BASE_DIR, 'qr_tablet.html')


def _lan_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return '127.0.0.1'


@app.route('/ping')
def ping():
    """Serve alla pagina del video per capire se gira sul computer del negozio.
    Restituisce anche l'IP di rete, cosi' il QR per il tablet si aggiorna da solo
    quando l'indirizzo del computer cambia."""
    return jsonify({'ok': True, 'server': 'biba-audio', 'ip': _lan_ip(), 'port': 5000})


def _prepare_scarf(start=0.0):
    """Prepara il wav della traccia foulard, gia' amplificata. In cache se parte da zero."""
    if start <= 0 and os.path.exists(TMP_SCARF_WAV):
        return TMP_SCARF_WAV
    audio = AudioSegment.from_mp3(SCARF_MP3) + VOLUME_BOOST_DB
    if start > 0:
        audio = audio[int(start * 1000):]
        tmp = TMP_SCARF_WAV.replace('.wav', '_seek.wav')
        audio.export(tmp, format='wav')
        return tmp
    audio.export(TMP_SCARF_WAV, format='wav')
    return TMP_SCARF_WAV


@app.route('/scarf/play')
def scarf_play():
    if not os.path.exists(SCARF_MP3):
        return jsonify({'error': 'scarf.mp3 non trovato'}), 404

    try:
        start = float(request.args.get('start', 0))
    except ValueError:
        start = 0.0

    def _play():
        with _lock:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except AttributeError:
                pass
            pygame.mixer.music.load(_prepare_scarf(start))
            # in loop: il video gira a 0,5x e dura il doppio della traccia
            pygame.mixer.music.play(-1)

    threading.Thread(target=_play, daemon=True).start()
    return jsonify({'ok': True, 'track': 'scarf', 'start': round(start, 1)})


@app.route('/scarf/pause')
def scarf_pause():
    pygame.mixer.music.pause()
    return jsonify({'ok': True})


@app.route('/scarf/resume')
def scarf_resume():
    pygame.mixer.music.unpause()
    return jsonify({'ok': True})


@app.route('/scarf/stop', methods=['GET', 'POST'])  # POST per sendBeacon
def scarf_stop():
    pygame.mixer.music.stop()
    return jsonify({'ok': True})


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
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except AttributeError:
                pass
            audio = AudioSegment.from_mp3(path) + VOLUME_BOOST_DB
            audio.export(TMP_WAV, format='wav')
            pygame.mixer.music.load(TMP_WAV)
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
