# 🎵 BPMKeySearch - Detector de Tom, BPM e Tempo (Spotify & YouTube)

Aplicativo moderno para desktop no Windows que detecta automaticamente a música que você está ouvindo no **Spotify** e no **YouTube** (Chrome, Edge, Firefox, Brave, Opera) e identifica em tempo real:

1. **Tom Musical (Key)**: Notação em português (ex: *Dó Maior*, *Lá Menor*) e internacional (*C Major*, *A Minor*), notas da escala e código **Camelot Wheel** (8B, 9A) com sugestões de mixagem harmônica para DJs.
2. **BPM (Beats Per Minute)**: Velocidade rítmica exata, visualizador de metrônomo pulsante em tempo real e classificação do andamento (*Allegro, Andante, Moderato, Presto*).
3. **Tempo & Compasso**: Compasso musical (*4/4, 3/4*), duração total, tempo decorrido ao vivo e cálculo de milissegundos por batida (*ms/beat*) para ajuste de Delays e Reverbs em DAWs.

---

## 🚀 Como Iniciar o Aplicativo

### Método Rápido (1 clique):
Basta dar dois cliques no arquivo:
```cmd
run.bat
```

### Ou pelo Terminal / PowerShell:
```powershell
cd C:\Users\facimoto\.gemini\antigravity\scratch\music_detector_app
& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" app.py
```

O aplicativo abrirá automaticamente em uma janela dedicada estilo Desktop (via Microsoft Edge App Mode ou navegador) no endereço `http://localhost:5055`.

---

## 🎧 Como Funciona a Detecção

- **Windows Media Session (GSMTC)**: O aplicativo escuta a API de transporte de mídia do Windows 10/11 (`GlobalSystemMediaTransportControlsSessionManager`), capturando instantaneamente o título, artista e status de reprodução do Spotify e dos navegadores ao reproduzir YouTube.
- **Krumhansl-Schmuckler Key Algorithm**: Algoritmo de inteligência musical que extrai o cromagrama das frequências de áudio (STFT / espectrograma com SciPy) e calcula a correlação de Pearson com os 24 perfis tonais para identificar o tom exato.
- **Detecção de BPM & Metrônomo**: Cruza os dados oficiais de masterização com autocorrelação espectral de envelopes de ataque (*onset detection*).
- **Busca Manual**: Possui uma barra de pesquisa no topo para você consultar o tom e BPM de qualquer música a qualquer momento sem precisar dar play.
- **Tap Tempo**: Você pode bater no ritmo com o mouse ou pressionar a barra de espaço para descobrir o BPM de qualquer batida manualmente.
- **Prévia de Áudio**: Botão para ouvir um trecho de 30 segundos da música detectada diretamente na interface.
- **Histórico**: Lista todas as músicas que você ouviu durante a sessão.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.14**
- **SciPy & NumPy**: Processamento de Sinal Digital (DSP), transformada de Fourier e correlação tonal.
- **Miniaudio**: Decodificação de áudio PCM de alta performance.
- **Bottle**: Servidor HTTP assíncrono e leve.
- **HTML5, Modern CSS & JavaScript**: Interface moderna em Modo Escuro (Cyberpunk/Studio), responsiva com Glassmorphism.
