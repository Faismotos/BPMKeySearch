import subprocess
import json
import re
import os

# PowerShell script to query Windows Media Transport Controls (GSMTC)
GSMTC_PS_SCRIPT = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
}

function Invoke-Async($asyncOp, [Type]$targetType) {
    if (-not $asyncOp) { return $null }
    try {
        $method = $asTaskGeneric.MakeGenericMethod($targetType)
        $task = $method.Invoke($null, @($asyncOp))
        return $task.GetAwaiter().GetResult()
    } catch {
        return $null
    }
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties, Windows.Media, ContentType = WindowsRuntime] | Out-Null

$data = @{
    source = ""
    title = ""
    artist = ""
    album = ""
    status = "Stopped"
    position = 0
    duration = 0
}

try {
    $mgrOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    $manager = Invoke-Async $mgrOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
    if ($manager) {
        $session = $manager.GetCurrentSession()
        if ($session) {
            $propOp = $session.TryGetMediaPropertiesAsync()
            $props = Invoke-Async $propOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
            $playback = $session.GetPlaybackInfo()
            $timeline = $session.GetTimelineProperties()

            $data.source = $session.SourceAppId
            if ($props) {
                $data.title = $props.Title
                $data.artist = $props.Artist
                $data.album = $props.AlbumTitle
            }
            if ($playback) {
                $data.status = $playback.PlaybackStatus.ToString()
            }
            if ($timeline) {
                $data.position = [math]::Round($timeline.Position.TotalSeconds, 1)
                $data.duration = [math]::Round($timeline.EndTime.TotalSeconds, 1)
            }
        }
    }
} catch {
    # Ignore GSMTC query failure
}

# Filter out BPMKeySearch's own window/session
if ($data.title -match "BPMKeySearch|KeyPulse" -or $data.artist -match "BPMKeySearch|KeyPulse") {
    $data.title = ""
    $data.artist = ""
    $data.source = ""
    $data.status = "Stopped"
}

# Fallback: Spotify Desktop Window title if GSMTC was empty
if (-not $data.title) {
    $spot = Get-Process spotify -ErrorAction SilentlyContinue | Where-Object { 
        $_.MainWindowTitle -and 
        $_.MainWindowTitle -ne "Spotify" -and 
        $_.MainWindowTitle -ne "Spotify Free" -and 
        $_.MainWindowTitle -ne "Spotify Premium" 
    } | Select-Object -First 1
    if ($spot) {
        $data.source = "Spotify.exe"
        $data.status = "Playing"
        $parts = $spot.MainWindowTitle -split " - ", 2
        if ($parts.Count -eq 2) {
            $data.artist = $parts[0].Trim()
            $data.title = $parts[1].Trim()
        } else {
            $data.title = $spot.MainWindowTitle
        }
    }
}

# Fallback: Browser playing YouTube
if (-not $data.title) {
    $browser = Get-Process chrome, msedge, brave, firefox, opera -ErrorAction SilentlyContinue | Where-Object { 
        $_.MainWindowTitle -match "YouTube" -and $_.MainWindowTitle -notmatch "KeyPulse"
    } | Select-Object -First 1
    if ($browser) {
        $data.source = $browser.ProcessName
        $data.status = "Playing"
        $raw = $browser.MainWindowTitle -replace " - YouTube.*$", ""
        $parts = $raw -split " - ", 2
        if ($parts.Count -eq 2) {
            $data.artist = $parts[0].Trim()
            $data.title = $parts[1].Trim()
        } else {
            $data.title = $raw.Trim()
        }
    }
}

$data | ConvertTo-Json -Compress
"""

def clean_track_metadata(raw_artist, raw_title):
    """
    Cleans up video/song titles, especially from YouTube and Spotify,
    removing artifacts like '(Official Video)', '[4K]', 'ft.', etc.
    """
    title = (raw_title or "").strip()
    artist = (raw_artist or "").strip()

    if any(app_name in title.lower() or app_name in artist.lower() for app_name in ["bpmkeysearch", "keypulse"]):
        return "", ""

    # If title has "Artist - Song Title" format and artist is generic or empty
    if " - " in title and (not artist or artist.lower() in ["youtube", "vevo", "music", "spotify"]):
        parts = title.split(" - ", 1)
        artist = parts[0].strip()
        title = parts[1].strip()

    # Regex patterns for junk in music video titles
    junk_patterns = [
        r"(?i)\(official\s*(music)?\s*(video|audio|lyric\s*video|visualizer|clip|hd|4k)\)",
        r"(?i)\[official\s*(music)?\s*(video|audio|lyric\s*video|visualizer|clip|hd|4k)\]",
        r"(?i)\((clipe\s*oficial|vídeo\s*oficial|video\s*oficial|audio\s*oficial|ao\s*vivo)\)",
        r"(?i)\[(clipe\s*oficial|vídeo\s*oficial|video\s*oficial|audio\s*oficial|ao\s*vivo)\]",
        r"(?i)\((lyrics?|letra|visualizer|audio|4k|hd|remastered|remasterizado)\)",
        r"(?i)\[(lyrics?|letra|visualizer|audio|4k|hd|remastered|remasterizado)\]",
        r"(?i)\(prod\.?\s*by[^\)]+\)",
        r"(?i)\[prod\.?\s*by[^\]]+\]",
        r"(?i)\(feat\.?[^\)]+\)",
        r"(?i)\[feat\.?[^\]]+\]",
        r"(?i)\(ft\.?[^\)]+\)",
        r"(?i)\[ft\.?[^\]]+\]",
        r"(?i)ft\.?\s+[a-zA-Z0-9\s,&]+",
        r"(?i)feat\.?\s+[a-zA-Z0-9\s,&]+"
    ]

    for pat in junk_patterns:
        title = re.sub(pat, "", title).strip()

    # Clean multiple spaces or leftover quotes/brackets
    title = re.sub(r'\s+', ' ', title).strip(" -[]()\"'")
    artist = re.sub(r'\s+', ' ', artist).strip(" -[]()\"'")

    return artist, title

def get_current_playing_media():
    """
    Executes the GSMTC script to detect currently playing song in Windows.
    Returns a dict with: source, title, artist, clean_title, clean_artist, status, position, duration
    """
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", GSMTC_PS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=4,
            startupinfo=startupinfo
        )

        output = proc.stdout.strip()
        if output:
            data = json.loads(output)
            clean_art, clean_tit = clean_track_metadata(data.get("artist", ""), data.get("title", ""))
            data["clean_artist"] = clean_art
            data["clean_title"] = clean_tit
            
            # Map source to readable name
            src = (data.get("source") or "").lower()
            if "spotify" in src:
                data["source_name"] = "Spotify"
                data["source_icon"] = "spotify"
            elif "chrome" in src or "msedge" in src or "brave" in src or "firefox" in src or "opera" in src:
                data["source_name"] = "YouTube / Web"
                data["source_icon"] = "youtube"
            elif src:
                data["source_name"] = data.get("source")
                data["source_icon"] = "media"
            else:
                data["source_name"] = "Nenhum"
                data["source_icon"] = "none"

            return data
    except Exception as e:
        pass

    return {
        "source": "",
        "source_name": "Nenhum",
        "source_icon": "none",
        "title": "",
        "artist": "",
        "clean_title": "",
        "clean_artist": "",
        "album": "",
        "status": "Stopped",
        "position": 0,
        "duration": 0
    }

if __name__ == "__main__":
    media = get_current_playing_media()
    print("Media detectada:", json.dumps(media, indent=2))
