import urllib.request
import urllib.parse
import json
import os
import re
import numpy as np
from scipy.signal import spectrogram

try:
    import miniaudio
except ImportError:
    miniaudio = None

CACHE_FILE = os.path.join(os.path.dirname(__file__), "tracks_cache.json")

# Note mappings in Portuguese and English
NOTE_NAMES_PT = ["Dó", "Dó#", "Ré", "Ré#", "Mi", "Fá", "Fá#", "Sol", "Sol#", "Lá", "Lá#", "Si"]
NOTE_NAMES_EN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Camelot codes for Major and Minor keys
# Major: 1B = B, 2B = F#, 3B = Db/C#, 4B = Ab/G#, 5B = Eb/D#, 6B = Bb/A#, 7B = F, 8B = C, 9B = G, 10B = D, 11B = A, 12B = E
CAMELOT_MAJOR = ["8B", "3B", "10B", "5B", "12B", "7B", "2B", "9B", "4B", "11B", "6B", "1B"]

# Minor: 1A = Abm, 2A = Ebm, 3A = Bbm, 4A = Fm, 5A = Cm, 6A = Gm, 7A = Dm, 8A = Am, 9A = Em, 10A = Bm, 11A = F#m, 12A = C#m
CAMELOT_MINOR = ["5A", "12A", "7A", "2A", "9A", "4A", "11A", "6A", "1A", "8A", "3A", "10A"]

# Major and Minor scale intervals (semitones)
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]

# Krumhansl-Schmuckler Key Profiles
KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_tempo_name(bpm):
    if bpm <= 0:
        return "Desconhecido"
    if bpm < 66:
        return "Largo (Muito Lento)"
    elif bpm < 76:
        return "Adagio (Lento e Expressivo)"
    elif bpm < 108:
        return "Andante (Passo Moderado)"
    elif bpm < 120:
        return "Moderato (Moderado)"
    elif bpm < 168:
        return "Allegro (Rápido e Animado)"
    else:
        return "Presto (Muito Rápido)"

def get_scale_notes(root_idx, is_major=True):
    intervals = MAJOR_INTERVALS if is_major else MINOR_INTERVALS
    notes_pt = [NOTE_NAMES_PT[(root_idx + step) % 12] for step in intervals]
    notes_en = [NOTE_NAMES_EN[(root_idx + step) % 12] for step in intervals]
    return {
        "pt": " - ".join(notes_pt),
        "en": " - ".join(notes_en),
        "notes_list": notes_en
    }

def get_harmonic_matches(camelot_code):
    if not camelot_code or camelot_code == "-":
        return []
    match = re.match(r"(\d+)([AB])", camelot_code)
    if not match:
        return []
    num = int(match.group(1))
    letter = match.group(2)
    other_letter = "B" if letter == "A" else "A"

    next_num = 1 if num == 12 else num + 1
    prev_num = 12 if num == 1 else num - 1

    return [
        {"code": f"{num}{letter}", "type": "Tom Idêntico"},
        {"code": f"{num}{other_letter}", "type": "Relativo Maior/Menor"},
        {"code": f"{next_num}{letter}", "type": "Subir Energia (+1)"},
        {"code": f"{prev_num}{letter}", "type": "Descer Energia (-1)"}
    ]

def estimate_bpm_from_audio(samples, sr):
    try:
        step = max(1, sr // 22050)
        s = samples[::step]
        fs = sr // step

        nperseg = int(fs * 0.02)
        noverlap = int(fs * 0.01)
        f, t, Sxx = spectrogram(s, fs=fs, nperseg=nperseg, noverlap=noverlap)

        freq_mask = (f >= 40) & (f <= 500)
        energy = np.sum(Sxx[freq_mask, :], axis=0) if np.any(freq_mask) else np.sum(Sxx, axis=0)

        onset_env = np.diff(energy, prepend=energy[0])
        onset_env[onset_env < 0] = 0
        std = np.std(onset_env)
        if std > 0:
            onset_env = (onset_env - np.mean(onset_env)) / std

        corr = np.correlate(onset_env, onset_env, mode='full')
        corr = corr[len(corr)//2:]

        hop_time = (nperseg - noverlap) / fs
        min_lag = int(round((60.0 / 210.0) / hop_time))
        max_lag = int(round((60.0 / 55.0) / hop_time))

        if max_lag <= min_lag or max_lag >= len(corr):
            return 120

        search_corr = corr[min_lag:max_lag]
        best_lag = min_lag + np.argmax(search_corr)
        bpm = 60.0 / (best_lag * hop_time)

        # Standard range adjustment
        while bpm < 65:
            bpm *= 2
        while bpm > 200:
            bpm /= 2

        return round(bpm)
    except Exception:
        return 120

def detect_key_from_audio(samples, sr):
    try:
        f, t, Sxx = spectrogram(samples, fs=sr, nperseg=4096, noverlap=2048)
        chroma = np.zeros(12)

        for i, freq in enumerate(f):
            if 60 <= freq <= 2500:
                midi = 69 + 12 * np.log2(freq / 440.0)
                pitch_class = int(round(midi)) % 12
                chroma[pitch_class] += np.sum(Sxx[i, :])

        norm = np.linalg.norm(chroma)
        if norm == 0:
            return {"key_pt": "Indefinido", "key_en": "Unknown", "camelot": "-", "scale": None}

        chroma = chroma / norm

        maj_p = KRUMHANSL_MAJOR / np.linalg.norm(KRUMHANSL_MAJOR)
        min_p = KRUMHANSL_MINOR / np.linalg.norm(KRUMHANSL_MINOR)

        best_corr = -1.0
        best_root = 0
        best_is_major = True

        for i in range(12):
            c_maj = np.corrcoef(chroma, np.roll(maj_p, i))[0, 1]
            if c_maj > best_corr:
                best_corr = c_maj
                best_root = i
                best_is_major = True

            c_min = np.corrcoef(chroma, np.roll(min_p, i))[0, 1]
            if c_min > best_corr:
                best_corr = c_min
                best_root = i
                best_is_major = False

        pt_name = f"{NOTE_NAMES_PT[best_root]} {'Maior' if best_is_major else 'Menor'}"
        en_name = f"{NOTE_NAMES_EN[best_root]} {'Major' if best_is_major else 'Minor'}"
        camelot = CAMELOT_MAJOR[best_root] if best_is_major else CAMELOT_MINOR[best_root]
        scale = get_scale_notes(best_root, best_is_major)

        return {
            "key_pt": pt_name,
            "key_en": en_name,
            "camelot": camelot,
            "scale": scale,
            "confidence": round(float(best_corr), 2)
        }
    except Exception as e:
        return {"key_pt": "Indefinido", "key_en": "Unknown", "camelot": "-", "scale": None}

def fetch_deezer_info(query):
    try:
        url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        if not data.get("data"):
            return None

        track = data["data"][0]
        track_id = track["id"]

        detail_url = f"https://api.deezer.com/track/{track_id}"
        req_det = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_det, timeout=5) as r:
            det = json.loads(r.read().decode('utf-8'))

        return {
            "title": det.get("title", track.get("title")),
            "artist": det.get("artist", {}).get("name", track.get("artist", {}).get("name")),
            "album": det.get("album", {}).get("title", track.get("album", {}).get("title")),
            "cover": det.get("album", {}).get("cover_big") or det.get("album", {}).get("cover_medium") or track.get("album", {}).get("cover_medium"),
            "bpm": det.get("bpm", 0),
            "duration": det.get("duration", track.get("duration", 0)),
            "preview": det.get("preview", track.get("preview")),
            "source_service": "Deezer"
        }
    except Exception:
        return None

def fetch_itunes_info(query):
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        if not data.get("results"):
            return None

        track = data["results"][0]
        artwork = track.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
        duration_s = int(track.get("trackTimeMillis", 0) / 1000)

        return {
            "title": track.get("trackName"),
            "artist": track.get("artistName"),
            "album": track.get("collectionName"),
            "cover": artwork,
            "bpm": 0,
            "duration": duration_s,
            "preview": track.get("previewUrl"),
            "source_service": "Apple Music"
        }
    except Exception:
        return None

def analyze_track(artist, title):
    """
    Given an artist and title, finds the track information, key, BPM, and musical attributes.
    """
    clean_query = f"{artist} {title}".strip()
    if not clean_query:
        return None

    cache_key = clean_query.lower()
    cache = load_cache()

    if cache_key in cache:
        return cache[cache_key]

    # Try Deezer first, fallback to iTunes
    info = fetch_deezer_info(clean_query)
    if not info:
        info = fetch_itunes_info(clean_query)

    if not info:
        # Fallback if both APIs fail: use the provided title & artist
        info = {
            "title": title or "Música Desconhecida",
            "artist": artist or "Artista Desconhecido",
            "album": "",
            "cover": "",
            "bpm": 0,
            "duration": 0,
            "preview": None,
            "source_service": "Local"
        }

    # Audio DSP Analysis (Key & BPM)
    key_info = {"key_pt": "Não detectado", "key_en": "Unknown", "camelot": "-", "scale": None}
    calculated_bpm = info.get("bpm", 0)

    if info.get("preview") and miniaudio is not None:
        try:
            req = urllib.request.Request(info["preview"], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as r:
                audio_bytes = r.read()

            decoded = miniaudio.decode(audio_bytes, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1)
            samples = np.array(decoded.samples, dtype=np.float32)
            sr = decoded.sample_rate

            key_info = detect_key_from_audio(samples, sr)

            if not calculated_bpm or calculated_bpm <= 0:
                calculated_bpm = estimate_bpm_from_audio(samples, sr)
        except Exception:
            pass

    bpm_val = round(calculated_bpm) if calculated_bpm and calculated_bpm > 0 else 120
    dur_sec = info.get("duration", 0)
    mins = dur_sec // 60
    secs = dur_sec % 60
    duration_formatted = f"{mins:02d}:{secs:02d}" if dur_sec > 0 else "--:--"

    # Milliseconds per beat (for delays, reverbs, echoes)
    ms_per_beat = round(60000 / bpm_val) if bpm_val > 0 else 500

    result = {
        "title": info.get("title") or title,
        "artist": info.get("artist") or artist,
        "album": info.get("album") or "",
        "cover": info.get("cover") or "",
        "preview_url": info.get("preview"),
        "key_pt": key_info.get("key_pt", "Desconhecido"),
        "key_en": key_info.get("key_en", "Unknown"),
        "camelot": key_info.get("camelot", "-"),
        "harmonic_matches": get_harmonic_matches(key_info.get("camelot")),
        "scale": key_info.get("scale"),
        "bpm": bpm_val,
        "bpm_exact": round(calculated_bpm, 1) if calculated_bpm else bpm_val,
        "tempo_name": get_tempo_name(bpm_val),
        "ms_per_beat": ms_per_beat,
        "time_signature": "4/4",
        "duration_sec": dur_sec,
        "duration_formatted": duration_formatted,
        "service": info.get("source_service", "Online")
    }

    # Save to cache
    cache[cache_key] = result
    save_cache(cache)

    return result

if __name__ == "__main__":
    res = analyze_track("Coldplay", "Viva La Vida")
    print(json.dumps(res, indent=2, ensure_ascii=False))
