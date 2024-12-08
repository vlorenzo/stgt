// Configuration and constants
const RECORDING_CONFIG = {
    SEGMENT_DURATION: 10 * 1000,
    SWITCH_BUFFER: 500,
    MAX_SEGMENTS: 60
};

class AudioRecorderManager {
    constructor(config) {
        this.config = config;
        this.recorderA = null;
        this.recorderB = null;
        this.activeRecorder = null;
        this.currentSegment = this.createNewSegment();
        this.isRecording = false;
        this.startTime = null;
        this.sessionId = null;
        this.switchTimeout = null;
        this.processingSegment = false;
        this.ui = new RecorderUI();
        this.statusPoller = new StatusPoller();
        this.processedSegments = new Map();
        this.mediaStream = null;
    }

    createNewSegment() {
        return {
            chunks: [],
            startTime: null,
            number: 1,
            processed: false
        };
    }

    async initializeRecorders() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 48000
                }
            });

            const options = {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            };

            this.recorderA = new MediaRecorder(this.mediaStream, options);
            this.recorderB = new MediaRecorder(this.mediaStream, options);

            // Set up event handlers
            [this.recorderA, this.recorderB].forEach(recorder => {
                recorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        this.currentSegment.chunks.push(event.data);
                    }
                };
                recorder.onerror = (event) => {
                    console.error('Recorder error:', event.error);
                };
            });

            this.activeRecorder = this.recorderA;
            return true;
        } catch (error) {
            console.error('Error initializing recorders:', error);
            this.ui.showError('Failed to initialize audio recording');
            return false;
        }
    }

    async start() {
        if (this.isRecording) return;
        
        const initialized = await this.initializeRecorders();
        if (!initialized) return;

        try {
            const response = await fetch('/api/long-recording/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.config)
            });

            if (!response.ok) throw new Error('Failed to create recording session');
            
            const data = await response.json();
            this.sessionId = data.session_id;
            this.isRecording = true;
            this.startTime = Date.now();
            this.currentSegment.startTime = this.startTime;
            
            // Start recording with timeslice for regular data chunks
            this.activeRecorder.start(500);
            this.statusPoller.start(this.sessionId);
            this.ui.startRecording();

            // Schedule first switch
            this.switchTimeout = setTimeout(() => {
                if (this.isRecording) {
                    this.switchRecorders();
                }
            }, RECORDING_CONFIG.SEGMENT_DURATION);
        } catch (error) {
            console.error('Error starting recording:', error);
            this.ui.showError('Failed to start recording');
            this.cleanup();
        }
    }

    async switchRecorders() {
        if (!this.isRecording || this.processingSegment) return;
        
        this.processingSegment = true;
        const currentRecorder = this.activeRecorder;
        const nextRecorder = currentRecorder === this.recorderA ? this.recorderB : this.recorderA;
        
        try {
            // Start next recorder
            nextRecorder.start(500);

            // Wait a moment to ensure next recorder is running
            await new Promise(resolve => setTimeout(resolve, 200));

            // Stop current recorder and collect data
            await this.finalizeCurrentSegment(currentRecorder, nextRecorder);
        } catch (error) {
            console.error('Error during recorder switch:', error);
            this.processingSegment = false;
        }
    }

    async finalizeCurrentSegment(currentRecorder, nextRecorder) {
        return new Promise((resolve) => {
            const segmentNumber = this.currentSegment.number;
            let finalDataReceived = false;

            const finalize = async () => {
                if (!finalDataReceived) return;

                try {
                    if (this.currentSegment.chunks.length === 0) {
                        throw new Error('No audio data collected');
                    }

                    // Create final blob
                    const blob = new Blob(this.currentSegment.chunks, {
                        type: 'audio/webm;codecs=opus'
                    });

                    if (blob.size < 1000) {
                        throw new Error('Audio data too small');
                    }

                    // Upload segment
                    await this.uploadSegment({
                        chunks: [blob],
                        number: segmentNumber
                    });

                    // Prepare for next segment
                    this.currentSegment = this.createNewSegment();
                    this.currentSegment.number = segmentNumber + 1;
                    this.currentSegment.startTime = Date.now();
                    this.activeRecorder = nextRecorder;

                    // Schedule next switch
                    this.processingSegment = false;
                    if (this.isRecording) {
                        this.switchTimeout = setTimeout(() => {
                            if (this.isRecording) {
                                this.switchRecorders();
                            }
                        }, RECORDING_CONFIG.SEGMENT_DURATION);
                    }

                    resolve();
                } catch (error) {
                    console.error('Error finalizing segment:', error);
                    this.processingSegment = false;
                    resolve();
                }
            };

            // Handle final data
            currentRecorder.addEventListener('dataavailable', (event) => {
                if (event.data && event.data.size > 0) {
                    this.currentSegment.chunks.push(event.data);
                }
                finalDataReceived = true;
                finalize();
            }, { once: true });

            // Request final data and stop
            if (currentRecorder.state === 'recording') {
                currentRecorder.requestData();
                currentRecorder.stop();
            } else {
                finalDataReceived = true;
                finalize();
            }
        });
    }

    async uploadSegment(segment) {
        const formData = new FormData();
        formData.append('audio', segment.chunks[0], `segment_${segment.number}.webm`);
        formData.append('segment_number', segment.number);
        formData.append('session_id', this.sessionId);
        
        Object.entries(this.config).forEach(([key, value]) => {
            formData.append(key, value);
        });

        try {
            const response = await fetch('/api/long-recording/segment', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.ui.updateResults(result);
        } catch (error) {
            console.error('Error uploading segment:', error);
            this.ui.showError(`Error uploading segment: ${error.message}`);
        }
    }

    async stop() {
        if (!this.isRecording) return;
        
        this.isRecording = false;
        if (this.switchTimeout) {
            clearTimeout(this.switchTimeout);
            this.switchTimeout = null;
        }
        
        while (this.processingSegment) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        await this.stopRecorders();
        await this.processFinalSegment();
        await new Promise(resolve => setTimeout(resolve, 500));
        await this.enhanceFinalText();
        
        this.ui.stopRecording();
        this.statusPoller.stop();
        this.cleanup();
    }

    async stopRecorders() {
        const stopRecorder = async (recorder) => {
            if (recorder && recorder.state === 'recording') {
                return new Promise((resolve) => {
                    recorder.addEventListener('stop', resolve, { once: true });
                    recorder.requestData();
                    recorder.stop();
                });
            }
        };

        await Promise.all([
            stopRecorder(this.recorderA),
            stopRecorder(this.recorderB)
        ]);
    }

    cleanup() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        this.recorderA = null;
        this.recorderB = null;
        this.activeRecorder = null;
    }

    async processFinalSegment() {
        if (this.currentSegment.chunks.length > 0) {
            const finalSegment = {
                chunks: this.currentSegment.chunks,
                number: this.currentSegment.number
            };
            await this.uploadSegment(finalSegment);
            this.processedSegments.set(finalSegment.number, true);
        }
    }

    async enhanceFinalText() {
        try {
            this.ui.showStatus('Processing final enhancement...');
            
            // Wait a moment to ensure all segments are processed
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const response = await fetch(`/api/long-recording/enhance/${this.sessionId}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to enhance final text');
            }
            
            const result = await response.json();
            this.ui.updateEnhancedResult(result);
        } catch (error) {
            console.error('Error during final enhancement:', error);
            this.ui.showError(error.message);
        }
    }
}

class RecorderUI {
    constructor() {
        this.elements = {
            startButton: document.getElementById('startLongRecording'),
            stopButton: document.getElementById('stopLongRecording'),
            status: document.getElementById('recordingStatus'),
            timer: document.getElementById('recordingTimer'),
            segmentCount: document.getElementById('chunkCount'),
            duration: document.getElementById('duration'),
            audioSource: document.getElementById('audioSourceSelect'),
            language: document.getElementById('languageSelect'),
            outputType: document.getElementById('outputTypeSelect'),
            model: document.getElementById('modelSelect'),
            enhancement: document.getElementById('enhancementModelSelect'),
            processingStatus: document.querySelector('.processing-status'),
            progressBar: document.getElementById('processProgress'),
            processedSegments: document.getElementById('processedChunks'),
            totalSegments: document.getElementById('totalChunks'),
            enhancedResult: document.getElementById('enhancedResult')
        };
        
        this.timerInterval = null;
        this.startTime = null;
    }

    startRecording() {
        this.elements.startButton.disabled = true;
        this.elements.stopButton.disabled = false;
        this.showStatus('Recording...');
        this.disableControls(true);
        this.startTimer();
    }

    stopRecording() {
        this.elements.startButton.disabled = false;
        this.elements.stopButton.disabled = true;
        this.showStatus('Recording completed');
        this.disableControls(false);
        this.stopTimer();
    }

    disableControls(disabled) {
        ['audioSource', 'language', 'outputType', 'model', 'enhancement'].forEach(control => {
            this.elements[control].disabled = disabled;
        });
    }

    startTimer() {
        this.startTime = Date.now();
        this.timerInterval = setInterval(() => this.updateTimer(), 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimer() {
        if (!this.startTime) return;
        
        const elapsed = Date.now() - this.startTime;
        const seconds = Math.floor((elapsed / 1000) % 60);
        const minutes = Math.floor((elapsed / (1000 * 60)) % 60);
        const hours = Math.floor(elapsed / (1000 * 60 * 60));
        
        this.elements.timer.textContent = 
            `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    showStatus(message) {
        this.elements.status.textContent = message;
    }

    showError(message) {
        this.showStatus(`Error: ${message}`);
    }

    updateResults(result) {
        if (result.text) {
            const transcriptionResults = document.getElementById('transcriptionResults');
            const segmentDiv = document.createElement('div');
            segmentDiv.className = 'segment-result';
            segmentDiv.innerHTML = `<p>Segment ${result.segment_number}: ${result.text}</p>`;
            
            // Insert in order
            const segments = transcriptionResults.getElementsByClassName('segment-result');
            let inserted = false;
            
            for (let i = 0; i < segments.length; i++) {
                const existingSegment = segments[i];
                const existingNumber = parseInt(existingSegment.textContent.match(/Segment (\d+):/)[1]);
                
                if (result.segment_number < existingNumber) {
                    transcriptionResults.insertBefore(segmentDiv, existingSegment);
                    inserted = true;
                    break;
                }
            }
            
            if (!inserted) {
                transcriptionResults.appendChild(segmentDiv);
            }
            
            segmentDiv.scrollIntoView({ behavior: 'smooth' });
        }
    }

    updateEnhancedResult(result) {
        if (result.enhanced_text) {
            this.elements.enhancedResult.innerHTML = `
                <h3>Enhanced Text</h3>
                <p>${result.enhanced_text}</p>
                <button class="copy-btn" onclick="copyToClipboard(this)">
                    <i class="fas fa-clipboard"></i> Copy
                </button>
            `;
        }
    }
}

class StatusPoller {
    constructor() {
        this.interval = null;
        this.sessionId = null;
    }

    start(sessionId) {
        this.sessionId = sessionId;
        this.interval = setInterval(() => this.poll(), 1000);
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    async poll() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`/api/long-recording/status/${this.sessionId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch status');
            }
            
            const status = await response.json();
            this.updateUI(status);
            
            if (status.status === 'completed') {
                this.stop();
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }

    updateUI(status) {
        const processingStatus = document.querySelector('.processing-status');
        const progressBar = document.getElementById('processProgress');
        const processedSegments = document.getElementById('processedChunks');
        const totalSegments = document.getElementById('totalChunks');
        
        if (processingStatus && progressBar && processedSegments && totalSegments) {
            processingStatus.style.display = 'block';
            progressBar.style.width = `${status.progress_percentage}%`;
            processedSegments.textContent = status.processed_segments;
            totalSegments.textContent = status.total_segments;
            
            if (status.status === 'completed') {
                processingStatus.style.display = 'none';
            }
        }
    }
}

// Initialize the recorder manager with configuration
function initializeRecorder() {
    const config = {
        audio_source: 'microphone',
        source_language: 'it',
        target_language: 'en',
        output_type: 'email',
        transcription_model: 'remote',
        enhancement_model: 'remote'
    };

    const recorder = new AudioRecorderManager(config);

    // Set up event listeners
    document.getElementById('startLongRecording').addEventListener('click', () => recorder.start());
    document.getElementById('stopLongRecording').addEventListener('click', () => recorder.stop());
    
    // Set up configuration change listeners
    const configElements = {
        audio_source: document.getElementById('audioSourceSelect'),
        source_language: document.getElementById('languageSelect'),
        output_type: document.getElementById('outputTypeSelect'),
        transcription_model: document.getElementById('modelSelect'),
        enhancement_model: document.getElementById('enhancementModelSelect')
    };

    Object.entries(configElements).forEach(([key, element]) => {
        element.addEventListener('change', () => {
            if (key === 'source_language') {
                const selectedOption = element.options[element.selectedIndex];
                config[key] = selectedOption.value;
                config.target_language = selectedOption.value;
            } else {
                config[key] = element.value;
            }
        });
    });
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', initializeRecorder);
    