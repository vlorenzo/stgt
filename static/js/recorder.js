let recorder;
const startButton = document.getElementById('startRecording');
const stopButton = document.getElementById('stopRecording');
const latestResultDiv = document.getElementById('latestResult');
const previousResultsDiv = document.getElementById('previousResults');
const recordingStatus = document.getElementById('recordingStatus');
const languageSelect = document.getElementById('languageSelect');

startButton.onclick = function() {
    startButton.disabled = true;
    stopButton.disabled = false;
    recordingStatus.textContent = "Recording...";
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function(stream) {
            recorder = RecordRTC(stream, {
                type: 'audio',
                mimeType: 'audio/webm',
                sampleRate: 44100,
                desiredSampRate: 16000,
                recorderType: RecordRTC.StereoAudioRecorder,
                numberOfAudioChannels: 1
            });
            
            recorder.startRecording();
        });
};

stopButton.onclick = function() {
    startButton.disabled = false;
    stopButton.disabled = true;
    recordingStatus.textContent = "Processing...";
    
    recorder.stopRecording(function() {
        let blob = recorder.getBlob();
        let formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        
        const selectedOption = languageSelect.options[languageSelect.selectedIndex];
        const language = {
            code: selectedOption.value,
            label: selectedOption.dataset.label
        };
        formData.append('language', JSON.stringify(language));
        
        fetch('/transcribe', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Move current latest result to previous results
            if (latestResultDiv.innerHTML !== '') {
                previousResultsDiv.insertAdjacentHTML('afterbegin', latestResultDiv.innerHTML);
            }

            // Add new result as the latest
            latestResultDiv.innerHTML = `
                <div class="result-item">
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
            recordingStatus.textContent = "An error occurred. Please try again.";
        });
    });
};

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
