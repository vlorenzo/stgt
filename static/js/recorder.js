let recorder;
const startButton = document.getElementById('startRecording');
const stopButton = document.getElementById('stopRecording');
const resultDiv = document.getElementById('result');

startButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function(stream) {
            recorder = RecordRTC(stream, {
                type: 'audio',
                mimeType: 'audio/wav',
                recorderType: RecordRTC.StereoAudioRecorder
            });
            recorder.startRecording();
            startButton.disabled = true;
            stopButton.disabled = false;
        });
}

function stopRecording() {
    recorder.stopRecording(function() {
        let blob = recorder.getBlob();
        sendAudioToServer(blob);
        startButton.disabled = false;
        stopButton.disabled = true;
    });
}

function sendAudioToServer(blob) {
    let formData = new FormData();
    formData.append('audio', blob, 'recording.wav');

    fetch('/transcribe', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        resultDiv.innerHTML = `
            <h2>Transcript:</h2>
            <p>${data.transcript}</p>
            <h2>Analysis:</h2>
            <p>${data.analysis}</p>
        `;
    })
    .catch(error => {
        console.error('Error:', error);
        resultDiv.innerHTML = 'An error occurred during transcription and analysis.';
    });
}
