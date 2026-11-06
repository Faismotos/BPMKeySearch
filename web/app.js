// BPMKeySearch Frontend Controller
let autoDetectEnabled = true;
let currentTrack = null;
let currentMediaStatus = null;
let isPreviewPlaying = false;
let sessionHistory = [];
let tapTimestamps = [];

// DOM Elements
const albumCover = document.getElementById('albumCover');
const vinylDisc = document.getElementById('vinylDisc');
const trackTitle = document.getElementById('trackTitle');
const trackArtist = document.getElementById('trackArtist');
const trackAlbum = document.getElementById('trackAlbum');
const sourceTag = document.getElementById('sourceTag');
const sourceLabel = document.getElementById('sourceLabel');
const sourceIcon = document.getElementById('sourceIcon');
const playbackState = document.getElementById('playbackState');
const playbackStateText = document.getElementById('playbackStateText');
const progressBar = document.getElementById('progressBar');
const currentTime = document.getElementById('currentTime');
const totalTime = document.getElementById('totalTime');
const btnPlayPreview = document.getElementById('btnPlayPreview');
const btnCopyData = document.getElementById('btnCopyData');
const btnRefresh = document.getElementById('btnRefresh');
const audioPreview = document.getElementById('audioPreview');

const camelotBadge = document.getElementById('camelotBadge');
const keyPt = document.getElementById('keyPt');
const keyEn = document.getElementById('keyEn');
const scaleNotes = document.getElementById('scaleNotes');
const harmonicList = document.getElementById('harmonicList');

const heroBpm = document.getElementById('heroBpm');
const tempoClassification = document.getElementById('tempoClassification');
const msPerBeat = document.getElementById('msPerBeat');
const bpmExact = document.getElementById('bpmExact');
const metronomePulse = document.getElementById('metronomePulse');

const timeSignature = document.getElementById('timeSignature');
const timeSignatureDesc = document.getElementById('timeSignatureDesc');
const totalDurationMetric = document.getElementById('totalDurationMetric');
const serviceMetric = document.getElementById('serviceMetric');
const keyModeMetric = document.getElementById('keyModeMetric');
const delayTip = document.getElementById('delayTip');

const monitorStatus = document.getElementById('monitorStatus');
const monitorStatusText = document.getElementById('monitorStatusText');
const btnToggleAuto = document.getElementById('btnToggleAuto');

const manualSearchInput = document.getElementById('manualSearchInput');
const btnSearch = document.getElementById('btnSearch');

const tapArea = document.getElementById('tapArea');
const tapBpmVal = document.getElementById('tapBpmVal');
const btnResetTap = document.getElementById('btnResetTap');

const historyList = document.getElementById('historyList');
const historyCount = document.getElementById('historyCount');
const toast = document.getElementById('toast');

// Format seconds into mm:ss
function formatTime(seconds) {
  if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Show Toast
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// Update UI with Track Analysis Data
function updateTrackUI(data, mediaInfo) {
  if (!data) return;

  const isSameTrack = currentTrack && 
    currentTrack.title.toLowerCase() === data.title.toLowerCase() && 
    currentTrack.artist.toLowerCase() === data.artist.toLowerCase();

  currentTrack = data;

  // Title, Artist, Album
  trackTitle.textContent = data.title || 'Música Desconhecida';
  trackArtist.textContent = data.artist || 'Artista Desconhecido';
  trackAlbum.textContent = data.album ? `Álbum: ${data.album}` : '';

  // Cover image
  if (data.cover) {
    albumCover.src = data.cover;
  } else {
    albumCover.src = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&auto=format&fit=crop&q=80";
  }

  // Source Badge
  sourceTag.className = 'source-tag';
  if (mediaInfo && mediaInfo.source_name) {
    sourceLabel.textContent = mediaInfo.source_name;
    if (mediaInfo.source_icon === 'spotify') {
      sourceTag.classList.add('spotify');
    } else if (mediaInfo.source_icon === 'youtube') {
      sourceTag.classList.add('youtube');
    }
  } else {
    sourceLabel.textContent = data.service || 'Online';
  }

  // Status & Vinyl rotation
  const isPlaying = mediaInfo && (mediaInfo.status === 'Playing' || mediaInfo.status === 'tocando');
  document.querySelector('.now-playing-card').classList.toggle('playing', isPlaying);

  playbackState.className = 'playback-state-badge';
  if (isPlaying) {
    playbackState.classList.add('playing');
    playbackStateText.textContent = 'Tocando Agora';
  } else if (mediaInfo && mediaInfo.status === 'Paused') {
    playbackState.classList.add('paused');
    playbackStateText.textContent = 'Pausado';
  } else {
    playbackStateText.textContent = 'Detectado';
  }

  // Progress Bar
  if (mediaInfo && mediaInfo.duration > 0) {
    const pos = mediaInfo.position || 0;
    const dur = mediaInfo.duration;
    currentTime.textContent = formatTime(pos);
    totalTime.textContent = formatTime(dur);
    const pct = Math.min(100, Math.max(0, (pos / dur) * 100));
    progressBar.style.width = `${pct}%`;
  } else if (data.duration_sec > 0) {
    currentTime.textContent = '00:00';
    totalTime.textContent = data.duration_formatted;
    progressBar.style.width = '0%';
  }

  // Preview Button
  if (data.preview_url) {
    btnPlayPreview.disabled = false;
    audioPreview.src = data.preview_url;
  } else {
    btnPlayPreview.disabled = true;
    audioPreview.src = '';
  }

  // Key & Scale
  keyPt.textContent = data.key_pt || '--';
  keyEn.textContent = data.key_en || '--';
  camelotBadge.textContent = data.camelot || '--';
  keyModeMetric.textContent = data.key_pt.includes('Menor') ? 'Menor (Minor)' : 'Maior (Major)';

  // Scale Notes
  scaleNotes.innerHTML = '';
  if (data.scale && data.scale.notes_list) {
    data.scale.notes_list.forEach(n => {
      const pill = document.createElement('span');
      pill.className = 'note-pill';
      pill.textContent = n;
      scaleNotes.appendChild(pill);
    });
  } else {
    scaleNotes.innerHTML = '<span class="note-pill">-</span>';
  }

  // Harmonic matches
  harmonicList.innerHTML = '';
  if (data.harmonic_matches && data.harmonic_matches.length) {
    data.harmonic_matches.forEach(m => {
      const tag = document.createElement('span');
      tag.className = 'harmonic-tag';
      tag.innerHTML = `<strong>${m.code}</strong> ${m.type}`;
      harmonicList.appendChild(tag);
    });
  } else {
    harmonicList.innerHTML = '<span class="harmonic-tag">-</span>';
  }

  // BPM
  heroBpm.textContent = data.bpm || '--';
  tempoClassification.textContent = data.tempo_name || 'Andamento';
  msPerBeat.textContent = `${data.ms_per_beat || 500} ms`;
  bpmExact.textContent = data.bpm_exact ? `${data.bpm_exact} BPM` : `${data.bpm} BPM`;
  delayTip.textContent = data.ms_per_beat || 500;

  // Pulse rate for metronome visualizer
  if (data.bpm && data.bpm > 0) {
    const durSec = 60 / data.bpm;
    document.documentElement.style.setProperty('--bpm-pulse-dur', `${durSec}s`);
    metronomePulse.classList.add('pulsing');
  } else {
    metronomePulse.classList.remove('pulsing');
  }

  // Time metrics
  timeSignature.textContent = data.time_signature || '4/4';
  totalDurationMetric.textContent = data.duration_formatted || '--:--';
  serviceMetric.textContent = data.service || 'Online';

  // Add to History if new
  if (!isSameTrack && data.title && data.title !== 'Música Desconhecida') {
    addToHistory(data);
  }
}

// Add Track to Session History
function addToHistory(track) {
  sessionHistory.unshift(track);
  if (sessionHistory.length > 20) sessionHistory.pop();

  historyCount.textContent = `${sessionHistory.length} músicas`;
  historyList.innerHTML = '';

  sessionHistory.forEach(item => {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.innerHTML = `
      <div class="history-meta">
        <img class="history-thumb" src="${item.cover || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100&auto=format&fit=crop&q=80'}" />
        <div>
          <div class="history-song">${item.title}</div>
          <div class="history-artist">${item.artist}</div>
        </div>
      </div>
      <div class="history-badges">
        <span class="h-badge-key">${item.key_pt} (${item.camelot})</span>
        <span class="h-badge-bpm">${item.bpm} BPM</span>
      </div>
    `;
    el.addEventListener('click', () => updateTrackUI(item, null));
    historyList.appendChild(el);
  });
}

// Fetch Status from Python Backend
async function fetchStatus() {
  if (!autoDetectEnabled) return;

  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();

    if (data.media) {
      currentMediaStatus = data.media;
      if (data.analysis) {
        updateTrackUI(data.analysis, data.media);
      } else if (data.media.title) {
        trackTitle.textContent = data.media.clean_title || data.media.title;
        trackArtist.textContent = data.media.clean_artist || data.media.artist || 'Detectando Tom & BPM...';
      }
    }
  } catch (err) {
    console.warn('Erro ao consultar /api/status:', err);
  }
}

// Manual Search
async function performSearch(query) {
  if (!query || !query.trim()) return;
  const q = query.trim();

  trackTitle.textContent = 'Buscando e analisando...';
  trackArtist.textContent = q;

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (data.error) {
      showToast('Música não encontrada!');
      return;
    }
    updateTrackUI(data, { source_name: 'Busca Manual', source_icon: 'none', status: 'Paused' });
    showToast(`Música encontrada: ${data.title}`);
  } catch (err) {
    showToast('Falha na busca.');
  }
}

// Tap Tempo Logic
function recordTap() {
  const now = performance.now();
  tapTimestamps.push(now);

  // Flash visual feedback
  tapArea.classList.add('tapped');
  setTimeout(() => tapArea.classList.remove('tapped'), 100);

  // Keep last 6 taps
  if (tapTimestamps.length > 8) {
    tapTimestamps.shift();
  }

  // Filter out taps older than 3 seconds
  tapTimestamps = tapTimestamps.filter(t => (now - t) < 3000);

  if (tapTimestamps.length >= 2) {
    const intervals = [];
    for (let i = 1; i < tapTimestamps.length; i++) {
      intervals.push(tapTimestamps[i] - tapTimestamps[i - 1]);
    }
    const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const bpm = Math.round(60000 / avgInterval);

    if (bpm >= 40 && bpm <= 260) {
      tapBpmVal.textContent = bpm;
    }
  }
}

function resetTap() {
  tapTimestamps = [];
  tapBpmVal.textContent = '--';
}

// Event Listeners
btnPlayPreview.addEventListener('click', () => {
  if (!audioPreview.src) return;
  if (isPreviewPlaying) {
    audioPreview.pause();
    isPreviewPlaying = false;
    btnPlayPreview.querySelector('span').textContent = 'Ouvir Prévia';
  } else {
    audioPreview.play();
    isPreviewPlaying = true;
    btnPlayPreview.querySelector('span').textContent = 'Pausar Prévia';
  }
});

audioPreview.addEventListener('ended', () => {
  isPreviewPlaying = false;
  btnPlayPreview.querySelector('span').textContent = 'Ouvir Prévia';
});

btnCopyData.addEventListener('click', () => {
  if (!currentTrack) {
    showToast('Nenhuma música selecionada para copiar!');
    return;
  }
  const text = `🎶 ${currentTrack.artist} - ${currentTrack.title} | Tom: ${currentTrack.key_pt} (${currentTrack.camelot}) | BPM: ${currentTrack.bpm} | Compasso: ${currentTrack.time_signature} | Duração: ${currentTrack.duration_formatted}`;
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copiado para a área de transferência!');
  });
});

btnRefresh.addEventListener('click', () => {
  fetchStatus();
  showToast('Atualizando detecção...');
});

btnToggleAuto.addEventListener('click', () => {
  autoDetectEnabled = !autoDetectEnabled;
  if (autoDetectEnabled) {
    monitorStatus.classList.remove('paused');
    monitorStatusText.textContent = 'Ouvindo Spotify & YouTube';
    showToast('Detecção automática ATIVADA');
  } else {
    monitorStatus.classList.add('paused');
    monitorStatusText.textContent = 'Detecção Pausada';
    showToast('Detecção automática PAUSADA');
  }
});

btnSearch.addEventListener('click', () => {
  performSearch(manualSearchInput.value);
});

manualSearchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    performSearch(manualSearchInput.value);
  }
});

tapArea.addEventListener('click', recordTap);
btnResetTap.addEventListener('click', resetTap);

// Spacebar Tap Tempo when not focusing an input
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && document.activeElement !== manualSearchInput) {
    e.preventDefault();
    recordTap();
  }
});

// Start Real-time Monitoring Loop (every 1.5s)
fetchStatus();
setInterval(fetchStatus, 1500);
