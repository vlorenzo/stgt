let recorder;
const startButton = document.getElementById('startRecording');
const stopButton = document.getElementById('stopRecording');
const latestResultDiv = document.getElementById('latestResult');
const previousResultsDiv = document.getElementById('previousResults');
const recordingStatus = document.getElementById('recordingStatus');
const languageSelect = document.getElementById('languageSelect');
const outputTypeSelect = document.getElementById('outputTypeSelect');
const modelSelect = document.getElementById('modelSelect');
const enhancementModelSelect = document.getElementById('enhancementModelSelect');
const audioSourceSelect = document.getElementById('audioSourceSelect');

let audioDevices = [];

// Function to detect and populate available audio devices
async function detectAudioDevices() {
    try {
        console.log('Starting audio device detection...');
        const devices = await navigator.mediaDevices.enumerateDevices();
        
        // Get both input and output devices
        const allAudioDevices = devices.filter(device => 
            device.kind === 'audioinput' || device.kind === 'audiooutput'
        );
        
        console.log('All audio devices:', allAudioDevices.map(device => ({
            label: device.label,
            deviceId: device.deviceId,
            kind: device.kind
        })));
        
        // Store only input devices for other functionalities
        audioDevices = devices.filter(device => device.kind === 'audioinput');
        
        // First try to find Aggregate Device, then fallback to other options
        const systemAudioDevice = allAudioDevices.find(device => 
            device.label.toLowerCase().includes('aggregate device')
        ) || allAudioDevices.find(device => 
            device.label.toLowerCase().includes('blackhole') || 
            device.label.toLowerCase().includes('black hole') ||
            device.label.toLowerCase().includes('multi-output device')
        );
        
        if (systemAudioDevice) {
            console.log('System audio device found:', {
                label: systemAudioDevice.label,
                deviceId: systemAudioDevice.deviceId,
                kind: systemAudioDevice.kind
            });
            
            // If it's an output device, find corresponding input
            if (systemAudioDevice.kind === 'audiooutput') {
                console.log('Found output device, searching for corresponding input...');
                const inputDevice = audioDevices.find(device => 
                    device.label.includes('Aggregate Device') ||
                    device.label.includes('BlackHole') ||
                    device.label.includes('Black Hole') ||
                    device.label.includes('Multi-Output')
                );
                
                if (inputDevice) {
                    console.log('Found corresponding input device:', {
                        label: inputDevice.label,
                        deviceId: inputDevice.deviceId,
                        kind: inputDevice.kind
                    });
                } else {
                    console.warn('No corresponding input device found');
                }
            }
        } else {
            console.log('No system audio device found among available devices');
            const systemOption = audioSourceSelect.querySelector('option[value="system"]');
            systemOption.disabled = true;
            systemOption.text = 'System Audio (No compatible device detected)';
        }
        
        return audioDevices;
    } catch (err) {
        console.error('Error in detectAudioDevices:', err);
        handleError('Failed to detect audio devices. Please check your browser permissions.');
        return [];
    }
}

// Initialize device detection
detectAudioDevices().catch(err => console.error('Initial device detection failed:', err));

startButton.onclick = async function() {
    console.log('Start button clicked');
    startButton.disabled = true;
    stopButton.disabled = false;
    recordingStatus.textContent = "Requesting audio access...";
    
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('getUserMedia not supported');
        handleError("Your browser doesn't support audio recording. Please try a modern browser like Chrome or Firefox.");
        return;
    }
    
    const selectedSource = audioSourceSelect.value;
    console.log('Selected audio source:', selectedSource);
    let constraints = { audio: true };
    
    if (selectedSource === 'system') {
        console.log('Attempting to use system audio');
        const devices = await navigator.mediaDevices.enumerateDevices();
        const allAudioDevices = devices.filter(device => 
            device.kind === 'audioinput' || device.kind === 'audiooutput'
        );
        
        // First try to find the output device, prioritizing Aggregate Device
        const outputDevice = allAudioDevices.find(device => 
            device.kind === 'audiooutput' && device.label.toLowerCase().includes('aggregate device')
        ) || allAudioDevices.find(device => 
            device.kind === 'audiooutput' && (
                device.label.toLowerCase().includes('blackhole') || 
                device.label.toLowerCase().includes('black hole') ||
                device.label.toLowerCase().includes('multi-output device')
            )
        );
        
        // Then find the corresponding input device
        const inputDevice = devices.filter(device => device.kind === 'audioinput').find(device => 
            device.label.toLowerCase().includes('aggregate device')
        ) || devices.filter(device => device.kind === 'audioinput').find(device => 
            device.label.toLowerCase().includes('blackhole') || 
            device.label.toLowerCase().includes('black hole') ||
            device.label.toLowerCase().includes('multi-output')
        );
        
        if (outputDevice) {
            console.log('🎧 Selected OUTPUT device for system audio:', {
                label: outputDevice.label,
                deviceId: outputDevice.deviceId,
                kind: outputDevice.kind
            });
        } else {
            console.warn('⚠️ No specific output device found for system audio');
        }

        if (inputDevice) {
            console.log('🎤 Selected INPUT device for recording:', {
                label: inputDevice.label,
                deviceId: inputDevice.deviceId,
                kind: inputDevice.kind
            });
        } else {
            console.error('❌ No suitable input device found for system audio');
            handleError("No suitable input device found for system audio. Please check your audio device configuration.");
            return;
        }
        
        constraints = {
            audio: {
                deviceId: { exact: inputDevice.deviceId },
                autoGainControl: false,
                echoCancellation: false,
                noiseSuppression: false,
                channelCount: 32,
                sampleRate: 44100
            }
        };
        console.log('🎛️ Audio configuration:', {
            deviceLabel: inputDevice.label,
            constraints: JSON.stringify(constraints, null, 2)
        });
    }
    
    try {
        console.log(`🎙️ Requesting audio stream for: ${selectedSource === 'system' ? 'System Audio' : 'Microphone'}`);
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('✅ Audio stream obtained successfully');
        
        const tracks = stream.getAudioTracks();
        const trackSettings = tracks.map(track => track.getSettings());
        console.log('📊 Active audio tracks:', tracks.map(track => ({
            label: track.label,
            enabled: track.enabled,
            muted: track.muted,
            readyState: track.readyState,
            settings: track.getSettings()
        })));
        console.log('🎚️ Track Settings Details:', trackSettings);
        
        recordingStatus.textContent = `Recording from ${selectedSource === 'system' ? 
            'System Audio (' + (tracks[0]?.label || 'Unknown Device') + ')' : 
            'Microphone'}...`;
        
        // Configure RecordRTC with optimized settings
        const recorderConfig = {
            type: 'audio',
            mimeType: 'audio/webm',
            numberOfAudioChannels: 32,
            sampleRate: 44100,
            desiredSampRate: 44100,
            recorderType: RecordRTC.MediaStreamRecorder,
            bufferSize: 16384,
            timeSlice: 1000,
            disableLogs: false,
            checkForInactiveTracks: true,
            onStateChanged: (state) => {
                console.log('🎙️ Recorder state changed:', state);
            },
            ondataavailable: (blob) => {
                const audioContext = new AudioContext();
                console.log('🔊 Audio Context State:', audioContext.state);
                console.log('🔊 Audio Context Sample Rate:', audioContext.sampleRate);
                
                console.log('📼 Audio data received:', {
                    source: selectedSource === 'system' ? 
                        'System Audio (' + (tracks[0]?.label || 'Unknown Device') + ')' : 
                        'Microphone',
                    blobType: blob.type,
                    blobSize: blob.size,
                    timestamp: new Date().toISOString(),
                    channels: trackSettings.map(s => s.channelCount).join(', '),
                    trackSettings: trackSettings
                });
            }
        };
        
        // Log detailed audio settings before starting recording
        const audioTracks = stream.getAudioTracks();
        const trackCapabilities = audioTracks.map(track => ({
            label: track.label,
            capabilities: track.getCapabilities(),
            settings: track.getSettings(),
            constraints: track.getConstraints()
        }));
        
        console.log('🎛️ Detailed Audio Track Information:', trackCapabilities);
        
        console.log('⚙️ Initializing recorder with config:', {
            source: selectedSource === 'system' ? 
                'System Audio (' + (tracks[0]?.label || 'Unknown Device') + ')' : 
                'Microphone',
            config: {
                ...recorderConfig,
                trackSettings: trackSettings,
                trackCapabilities: trackCapabilities
            }
        });
        
        recorder = RecordRTC(stream, recorderConfig);
        
        // Add audio processing to analyze channels
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyzer = audioContext.createAnalyser();
        source.connect(analyzer);
        
        // Log channel information
        console.log('📊 Audio Channel Configuration:', {
            contextChannels: audioContext.destination.channelCount,
            maxChannels: audioContext.destination.maxChannelCount,
            sourceChannels: source.channelCount,
            analyzerChannels: analyzer.channelCount
        });
        
        console.log('▶️ Starting recording');
        recorder.startRecording();
    } catch (err) {
        console.error('❌ Error accessing audio:', {
            source: selectedSource === 'system' ? 'System Audio' : 'Microphone',
            error: err,
            name: err.name,
            message: err.message,
            constraint: err.constraint
        });
        handleError(`Error accessing the ${selectedSource}: ${err.message}`);
    }
};

stopButton.onclick = function() {
    console.log('Stop button clicked');
    if (!recorder) {
        console.error('No active recorder found');
        handleError("No active recording found.");
        return;
    }
    
    startButton.disabled = false;
    stopButton.disabled = true;
    recordingStatus.textContent = "Processing...";
    
    recorder.stopRecording(function() {
        console.log('Recording stopped, getting blob');
        let blob = recorder.getBlob();
        console.log('Blob created:', {
            type: blob.type,
            size: blob.size
        });
        sendAudioToServer(blob);
    });
};

// Add event listener for audio source changes
audioSourceSelect.addEventListener('change', function() {
    const selectedSource = this.value;
    console.log('Audio source changed to:', selectedSource);
    
    if (selectedSource === 'system') {
        const blackholeDevice = audioDevices.find(device => 
            device.label.toLowerCase().includes('blackhole') || 
            device.label.toLowerCase().includes('black hole') ||
            device.label.toLowerCase().includes('multi-output device')
        );
        
        if (!blackholeDevice) {
            console.warn('BlackHole device not found after source change');
            handleError("BlackHole audio device not detected. Please make sure it's properly installed and configured.");
            this.value = 'microphone';
        } else {
            console.log('BlackHole device available:', {
                label: blackholeDevice.label,
                deviceId: blackholeDevice.deviceId
            });
        }
    }
});

function handleError(message) {
    console.error('Error occurred:', message);
    const formattedMessage = message.replace(/\n/g, '<br>');
    recordingStatus.innerHTML = `<div class="error-message">${formattedMessage}</div>`;
    startButton.disabled = false;
    stopButton.disabled = true;
}

function sendAudioToServer(blob) {
    console.log('Preparing to send audio to server');
    let formData = new FormData();
    formData.append('audio', blob, 'recording.webm');
    
    const selectedLanguageOption = languageSelect.options[languageSelect.selectedIndex];
    const language = {
        code: selectedLanguageOption.value,
        label: selectedLanguageOption.dataset.label
    };
    formData.append('language', JSON.stringify(language));
    
    const outputType = outputTypeSelect.value;
    formData.append('output_type', outputType);
    
    const useLocalModel = modelSelect.value === 'local';
    formData.append('use_local_model', useLocalModel);
    
    const useLocalEnhancement = enhancementModelSelect.value === 'local';
    formData.append('use_local_enhancement', useLocalEnhancement);
    
    console.log('Sending audio with parameters:', {
        language,
        outputType,
        useLocalModel,
        useLocalEnhancement
    });
    
    recordingStatus.textContent = `Processing with ${useLocalModel ? 'local' : 'remote'} Whisper model and ${useLocalEnhancement ? 'local Llama' : 'GPT'} enhancement...`;
    
    fetch('/transcribe', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Server response received:', data);
        if (data.error) {
            console.error('Server returned error:', data.error);
            handleError(data.error);
            return;
        }
        
        // Move current latest result to previous results
        if (latestResultDiv.innerHTML !== '') {
            previousResultsDiv.insertAdjacentHTML('afterbegin', latestResultDiv.innerHTML);
        }

        // Add new result as the latest
        latestResultDiv.innerHTML = `
            <div class="result-item">
                <h2>Audio Duration: <span class="timestamp">${data.audio_duration}s</span></h2>
                <h2>Transcript: <span class="timestamp">[${data.transcription_time}]</span></h2>
                <p>${data.transcript}</p>
                <h2>Analysis: <span class="timestamp">[${data.analysis_time}]</span>
                    <button class="copy-btn" onclick="copyToClipboard('analysis-text-${data.transcription_time}', this)">
                        <i class="fas fa-clipboard"></i>
                    </button>
                </h2>
                <p id="analysis-text-${data.transcription_time}">${data.analysis}</p>
            </div>
        `;
        recordingStatus.textContent = "";
        console.log('Results displayed successfully');

        // Scroll to top of the page
        window.scrollTo(0, 0);
    })
    .catch(error => {
        console.error('Network or server error:', error);
        handleError("An error occurred while processing the audio. Please try again.");
    });
}

function copyToClipboard(elementId, buttonElement) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        // Change icon to checkmark
        buttonElement.innerHTML = '<i class="fas fa-check"></i>';
        buttonElement.classList.add('copied');
        
        // Reset icon after 2 seconds
        setTimeout(() => {
            buttonElement.innerHTML = '<i class="fas fa-clipboard"></i>';
            buttonElement.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}
