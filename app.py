import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import threading
import json
import webbrowser
import subprocess
from bottle import Bottle, static_file, request, response

import media_detector
import music_analyzer

app = Bottle()
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

# Shared state between background monitor and HTTP server
app_state = {
    "media": None,
    "analysis": None,
    "last_track_key": None,
    "is_analyzing": False
}
state_lock = threading.Lock()

def background_media_monitor():
    """
    Polls Windows GSMTC every 1.5 seconds.
    If a new song is detected on Spotify or YouTube, triggers musical analysis.
    """
    while True:
        try:
            media_info = media_detector.get_current_playing_media()
            clean_title = media_info.get("clean_title") or media_info.get("title")
            clean_artist = media_info.get("clean_artist") or media_info.get("artist")

            current_key = f"{clean_artist} - {clean_title}".strip().lower()

            with state_lock:
                app_state["media"] = media_info

                # If we have a valid song and it changed
                if clean_title and current_key != app_state["last_track_key"]:
                    app_state["last_track_key"] = current_key
                    app_state["is_analyzing"] = True

            if clean_title and current_key == app_state["last_track_key"] and app_state["is_analyzing"]:
                # Run musical analysis (Krumhansl-Schmuckler Key + BPM + Time)
                analysis = music_analyzer.analyze_track(clean_artist, clean_title)
                with state_lock:
                    app_state["analysis"] = analysis
                    app_state["is_analyzing"] = False

        except Exception as e:
            pass

        time.sleep(1.5)

# --- HTTP Endpoints ---

@app.route('/')
def index():
    return static_file('index.html', root=WEB_DIR)

@app.route('/<filename:path>')
def static_assets(filename):
    return static_file(filename, root=WEB_DIR)

@app.route('/api/status')
def api_status():
    response.content_type = 'application/json'
    with state_lock:
        return json.dumps({
            "media": app_state["media"],
            "analysis": app_state["analysis"],
            "is_analyzing": app_state["is_analyzing"]
        }, ensure_ascii=False)

@app.route('/api/search')
def api_search():
    response.content_type = 'application/json'
    query = request.query.get('q', '').strip()
    if not query:
        return json.dumps({"error": "Empty query"})

    # If query contains " - ", split artist and title
    if " - " in query:
        parts = query.split(" - ", 1)
        artist, title = parts[0].strip(), parts[1].strip()
    else:
        artist, title = "", query

    analysis = music_analyzer.analyze_track(artist, title)
    if not analysis:
        return json.dumps({"error": "Not found"})
    return json.dumps(analysis, ensure_ascii=False)

def run_server(port=5000):
    app.run(host='127.0.0.1', port=port, quiet=True)

def open_desktop_window(url):
    """
    Tries to open in Microsoft Edge App Mode (frameless native desktop window),
    or falls back to the system default browser.
    """
    time.sleep(1.0)
    # Check if Microsoft Edge is installed to run in clean --app mode
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)

    if edge_exe:
        try:
            subprocess.Popen([edge_exe, f"--app={url}", "--window-size=1080,780"])
            return
        except Exception:
            pass

    # Fallback to standard browser
    webbrowser.open(url)

def main():
    port = 5055

    # 1. Start background media listener thread
    monitor_thread = threading.Thread(target=background_media_monitor, daemon=True)
    monitor_thread.start()

    # 2. Launch desktop window in separate thread
    app_url = f"http://127.0.0.1:{port}"
    threading.Thread(target=open_desktop_window, args=(app_url,), daemon=True).start()

    print("=" * 60)
    print(" 🎵 BPMKeySearch - Detector Musical (Spotify & YouTube)")
    print(f" 🚀 Aplicativo aberto em: {app_url}")
    print(" 🎧 Monitorando reprodução em tempo real...")
    print("    Pressione Ctrl+C para encerrar.")
    print("=" * 60)

    # 3. Start web server
    run_server(port=port)

if __name__ == "__main__":
    main()
