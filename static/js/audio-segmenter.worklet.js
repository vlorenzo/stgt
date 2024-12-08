// AudioWorklet processor for continuous audio processing and segmentation
class AudioSegmenterProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.isRecording = false;
        this.sampleCount = 0;
        this.segmentSamples = 128000 * 15; // ~15 seconds at 128kHz
    }

    process(inputs, outputs) {
        const input = inputs[0];
        const output = outputs[0];
        
        if (!this.isRecording || !input || !input[0] || input[0].length === 0) {
            return true;
        }

        // Copy input to output
        for (let channel = 0; channel < input.length; channel++) {
            const inputChannel = input[channel];
            const outputChannel = output[channel];
            for (let i = 0; i < inputChannel.length; i++) {
                outputChannel[i] = inputChannel[i];
                this.sampleCount++;
            }
        }

        // Check if we've reached segment boundary
        if (this.sampleCount >= this.segmentSamples) {
            this.port.postMessage({ message: 'segment_boundary' });
            this.sampleCount = 0;
        }

        return true;
    }

    port.onmessage = (event) => {
        if (event.data.command === 'start') {
            this.isRecording = true;
            this.sampleCount = 0;
        } else if (event.data.command === 'stop') {
            this.isRecording = false;
            this.sampleCount = 0;
        }
    }
}

registerProcessor('audio-segmenter', AudioSegmenterProcessor); 