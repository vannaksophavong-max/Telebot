document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    const body = document.body;
    
    const textInput = document.getElementById('text-input');
    const charCurrent = document.getElementById('char-current');
    
    const form = document.getElementById('tts-form');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');
    
    const errorMsg = document.getElementById('error-message');
    const playerContainer = document.getElementById('player-container');
    const audioPlayer = document.getElementById('audio-player');
    const downloadBtn = document.getElementById('download-btn');
    
    const historyList = document.getElementById('history-list');

    // Theme Toggle
    const currentTheme = localStorage.getItem('theme') || 'dark';
    if (currentTheme === 'light') {
        body.classList.remove('dark-mode');
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        body.classList.add('dark-mode');
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }

    themeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        const isDark = body.classList.contains('dark-mode');
        
        if (isDark) {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            localStorage.setItem('theme', 'dark');
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            localStorage.setItem('theme', 'light');
        }
    });

    // Character Count
    textInput.addEventListener('input', () => {
        charCurrent.textContent = textInput.value.length;
    });

    // History Functions
    const loadHistory = () => {
        const history = JSON.parse(localStorage.getItem('tts_history') || '[]');
        historyList.innerHTML = '';
        
        if (history.length === 0) {
            historyList.innerHTML = '<li style="color: var(--text-secondary); font-size: 0.85rem;">No recent generations</li>';
            return;
        }

        // Limit to 5 items
        history.slice(0, 5).forEach((item) => {
            const li = document.createElement('li');
            li.className = 'history-item';
            
            const textPreview = item.text.length > 40 ? item.text.substring(0, 40) + '...' : item.text;
            
            li.innerHTML = `
                <div class="history-text" title="${item.text}">${textPreview}</div>
                <div class="history-meta">
                    <span>${item.voice}</span>
                    <button class="play-history-btn" data-url="${item.url}" aria-label="Play">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>
            `;
            
            const playBtn = li.querySelector('.play-history-btn');
            playBtn.addEventListener('click', () => {
                playAudio(item.url);
            });
            
            historyList.appendChild(li);
        });
    };

    const addToHistory = (text, voice, url) => {
        const history = JSON.parse(localStorage.getItem('tts_history') || '[]');
        history.unshift({ text, voice, url, timestamp: new Date().getTime() });
        localStorage.setItem('tts_history', JSON.stringify(history));
        loadHistory();
    };

    const playAudio = (url) => {
        audioPlayer.src = url;
        playerContainer.style.display = 'block';
        audioPlayer.play().catch(e => console.error("Playback failed", e));
        downloadBtn.href = url;
    };

    loadHistory();

    // Form Submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await submitText(textInput.value, true);
    });

    // Voice Preview
    const previewBtn = document.getElementById('preview-btn');
    previewBtn.addEventListener('click', async () => {
        const originalIcon = previewBtn.innerHTML;
        previewBtn.innerHTML = '<div class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></div>';
        previewBtn.disabled = true;
        
        try {
            await submitText("This is a preview of the selected voice.", false);
        } catch (error) {
            console.error(error);
        } finally {
            previewBtn.innerHTML = originalIcon;
            previewBtn.disabled = false;
        }
    });

    const submitText = async (textToSynthesize, isMainForm) => {
        const formData = new FormData(form);
        formData.set('text', textToSynthesize);
        
        if (isMainForm) {
            generateBtn.disabled = true;
            btnText.style.display = 'none';
            spinner.style.display = 'block';
            errorMsg.style.display = 'none';
        }
        
        try {
            const response = await fetch('/generate/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                playAudio(data.audio_url);
                if (isMainForm) {
                    downloadBtn.download = data.filename;
                    const voiceSelect = document.getElementById('voice-select');
                    const voiceName = voiceSelect.options[voiceSelect.selectedIndex].text;
                    addToHistory(textToSynthesize, voiceName, data.audio_url);
                }
            } else {
                throw new Error(data.error || 'Failed to generate TTS');
            }
        } catch (error) {
            if (isMainForm) {
                errorMsg.textContent = error.message;
                errorMsg.style.display = 'block';
            } else {
                alert("Preview failed: " + error.message);
            }
        } finally {
            if (isMainForm) {
                generateBtn.disabled = false;
                btnText.style.display = 'block';
                spinner.style.display = 'none';
            }
        }
    };
});
