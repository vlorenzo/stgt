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

startButton.onclick = function() {
    startButton.disabled = true;
    stopButton.disabled = false;
    recordingStatus.textContent = "Requesting microphone access...";
    
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        handleError("Your browser doesn't support audio recording. Please try a modern browser like Chrome or Firefox.");
        return;
    }
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function(stream) {
            recordingStatus.textContent = "Recording...";
            recorder = RecordRTC(stream, {
                type: 'audio',
                mimeType: 'audio/webm',
                sampleRate: 44100,
                desiredSampRate: 16000,
                recorderType: RecordRTC.StereoAudioRecorder,
                numberOfAudioChannels: 1
            });
            
            recorder.startRecording();
        })
        .catch(function(err) {
            handleError("Error accessing the microphone: " + err.message);
        });
};

stopButton.onclick = function() {
    if (!recorder) {
        handleError("No active recording found.");
        return;
    }
    
    startButton.disabled = false;
    stopButton.disabled = true;
    recordingStatus.textContent = "Processing...";
    
    recorder.stopRecording(function() {
        let blob = recorder.getBlob();
        sendAudioToServer(blob);
    });
};

function handleError(message) {
    console.error(message);
    const formattedMessage = message.replace(/\n/g, '<br>');
    recordingStatus.innerHTML = `<div class="error-message">${formattedMessage}</div>`;
    startButton.disabled = false;
    stopButton.disabled = true;
}

function sendAudioToServer(blob) {
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
    
    recordingStatus.textContent = `Processing with ${useLocalModel ? 'local' : 'remote'} Whisper model and ${useLocalEnhancement ? 'local Llama' : 'GPT'} enhancement...`;
    
    fetch('/transcribe', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
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

        // Scroll to top of the page
        window.scrollTo(0, 0);
    })
    .catch(error => {
        console.error('Error:', error);
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
