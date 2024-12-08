/**
 * WebAudio-based recorder manager for handling continuous audio recording and segmentation
 */
class WebAudioRecorder {
    constructor(config) {
        this.config = config;
        this.chunks = [];
        this.currentSegment = 1;
        this.isRecording = false;
        this.audioContext = null;
        this.mediaRecorder = null;
        this.processorNode = null;
        this.sourceNode = null;
        this.stream = null;
    }

    async initialize() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioContext = new AudioContext();
            this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
            
            await this.audioContext.audioWorklet.addModule('static/js/audio-segmenter.worklet.js');
            this.processorNode = new AudioWorkletNode(this.audioContext, 'audio-segmenter');
            
            this.sourceNode.connect(this.processorNode);
            this.processorNode.connect(this.audioContext.destination);
            
            // Set up event handlers for segment boundaries
            this.processorNode.port.onmessage = async (event) => {
                if (event.data.message === 'segment_boundary') {
                    await this.finalizeCurrentSegment();
                }
            };
            
            document.dispatchEvent(new Event('recorderInitialized'));
        } catch (error) {
            console.error('Initialization error:', error);
            throw error;
        }
    }

    async start() {
        if (this.isRecording) return;
        
        try {
            // Create a new MediaRecorder for this segment
            const outputStream = this.processorNode.port.postMessage({ command: 'start' });
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            });
            
            this.chunks = [];
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.chunks.push(event.data);
                }
            };
            
            this.mediaRecorder.start(100); // Collect chunks every 100ms
            this.isRecording = true;
            
            document.dispatchEvent(new Event('recordingStarted'));
        } catch (error) {
            console.error('Start recording error:', error);
            throw error;
        }
    }

    async stop() {
        if (!this.isRecording) return;
        
        try {
            // Stop the current segment and clean up
            await this.finalizeCurrentSegment();
            this.processorNode.port.postMessage({ command: 'stop' });
            
            // Clean up resources
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            if (this.audioContext) {
                await this.audioContext.close();
            }
            
            this.isRecording = false;
            document.dispatchEvent(new Event('recordingStopped'));
        } catch (error) {
            console.error('Stop recording error:', error);
            throw error;
        }
    }

    async finalizeCurrentSegment() {
        if (!this.mediaRecorder || this.chunks.length === 0) return;
        
        try {
            // Stop current MediaRecorder
            if (this.mediaRecorder.state === 'recording') {
                await new Promise(resolve => {
                    this.mediaRecorder.onstop = resolve;
                    this.mediaRecorder.stop();
                });
            }
            
            // Create blob and send segment
            const segmentBlob = new Blob(this.chunks, { type: 'audio/webm;codecs=opus' });
            await this.sendSegment(segmentBlob);
            
            // Prepare for next segment
            this.chunks = [];
            this.currentSegment++;
            
            // Start new MediaRecorder if still recording
            if (this.isRecording) {
                this.mediaRecorder = new MediaRecorder(this.stream, {
                    mimeType: 'audio/webm;codecs=opus',
                    audioBitsPerSecond: 128000
                });
                
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.chunks.push(event.data);
                    }
                };
                
                this.mediaRecorder.start(100);
            }
        } catch (error) {
            console.error('Finalize segment error:', error);
            throw error;
        }
    }

    async sendSegment(blob) {
        const formData = new FormData();
        formData.append('segment_number', this.currentSegment);
        formData.append('session_id', window.sessionId);
        formData.append('audio', blob, `segment_${this.currentSegment}.webm`);
        
        // Add configuration parameters
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
            
            return await response.json();
        } catch (error) {
            console.error('Send segment error:', error);
            throw error;
        }
    }
} 