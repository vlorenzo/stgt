# STGT - Speech To Generative Text

A Flask-based web application that transcribes speech to text and enhances it using AI. The application supports both OpenAI's Whisper API and local Whisper model for transcription, with special optimizations for macOS.

## Features

- Real-time audio recording through web browser
- Dual transcription options:
  - OpenAI Whisper API (requires API key, faster)
  - Local Whisper model (offline capable, no API costs)
- Multiple Whisper model options (base, small, medium, large, turbo)
- Text enhancement options:
  - OpenAI GPT-4 (requires API key)
  - Local LLM via Ollama (offline capable, no API costs)
- Support for multiple output formats:
  - Email
  - WhatsApp messages
  - AI prompts
  - General text
- Clean and responsive web interface
- Detailed logging system

## Prerequisites

- macOS (tested on Sonoma 14.0+)
- Python 3.10 
- Homebrew (for installing ffmpeg)
- OpenAI API key (optional, for OpenAI services)
- Ollama (optional, for local LLM capabilities)

## Installation

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install ffmpeg** (required for local Whisper model):
   ```bash
   brew install ffmpeg
   ```

3. **Install Ollama** (optional, for local LLM capabilities):
   ```bash
   brew install ollama
   ```

4. **Download and run the Llama2 model** (if using local LLM):
   ```bash
   ollama pull llama2
   ```

4. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/stgt.git
   cd stgt
   ```

5. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

6. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

7. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

8. **Generate SSL certificate** (required for microphone access):
   ```bash
   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
   ```
   When prompted for "Common Name", enter `localhost`

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Access the application**:
   - Open your browser and go to `https://localhost:5001`
   - Accept the self-signed certificate warning (this is safe for local development)

## Usage

1. **Choose your transcription settings**:
   - **Language**: Select target language (default is Italian)
   - **Output Format**: Choose between email, WhatsApp, AI prompt, or general text
   - **Transcription Model**: 
     - Remote (OpenAI API) - Faster, requires internet
     - Local (Whisper) - Works offline, runs on your machine
   - **Text Enhancement**:
     - Remote (OpenAI GPT) - More powerful, requires API key
     - Local (Llama2) - Works offline, runs on your machine

2. **Record your speech**:
   - Click "Start Recording"
   - Speak into your microphone
   - Click "Stop Recording" when done

3. **View Results**:
   - Original transcription will appear
   - Enhanced/translated text will follow
   - Use the copy button to copy the enhanced text

## Transcription Models

When using the local Whisper model, you can choose between different model sizes:
- `base`: Fastest, lowest accuracy
- `small`: Good balance for general use
- `medium`: Better accuracy, slower
- `large`: Best accuracy, requires more memory
- `turbo`: Latest model, optimized for speed

To change the model, modify `model_size` in `src/services/transcription.py`:
```python
self.model = whisper.load_model("base")  # Change "base" to your preferred model
```

## Text Enhancement Models

The application supports two modes for text enhancement:

### OpenAI GPT
- Requires API key
- More powerful and accurate
- Supports all languages
- Faster processing

### Local LLM (via Ollama)
- Completely offline operation
- No API costs
- Uses Llama2 model by default
- Can be customized with different models
- Processing speed depends on your hardware

To use a different Ollama model, modify the model name in `src/services/text_enhancement.py`:
```python
self.model_name = "llama2"  # Change to your preferred model
```

Available models can be listed using:
```bash
ollama list
```

## Logging

The application provides two levels of logging:
- **Console**: Shows main steps and timing in color-coded format
- **File**: Detailed debug information in `app.log`

Log files rotate automatically when they reach 1MB, keeping up to 10 backup files.

## Troubleshooting

1. **Microphone Access Issues**:
   - Ensure you've granted browser permission for microphone
   - Check that you're using HTTPS (required for microphone access)
   - Try restarting your browser if permissions don't appear

2. **Certificate Warnings**:
   - The warning about self-signed certificate is normal in development
   - Click "Advanced" and "Proceed to localhost" in your browser

3. **Local Whisper Model Issues**:
   - Verify ffmpeg is installed: `brew list ffmpeg`
   - Check Python environment is activated
   - Ensure enough disk space for model downloads

4. **OpenAI API Issues**:
   - Verify your API key in `.env`
   - Check your OpenAI account has available credits
   - Ensure internet connectivity

## Project Structure

```
project_root/
├── src/                    # Source code directory
│   ├── config/            # Configuration modules
│   ├── services/          # Business logic
│   ├── routes/            # API routes
│   └── utils/             # Utility functions
├── static/                # Static files (CSS, JS)
├── templates/             # HTML templates
└── app.py                # Main application entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Audio Input Options

The application supports two audio input sources:
1. **Microphone**: Direct microphone input for voice recording
2. **System Audio**: Capture system audio output using BlackHole

### Setting up System Audio Capture

To capture system audio, you'll need to install and configure BlackHole:

1. **Install BlackHole**:
   ```bash
   brew install blackhole-2ch
   ```

2. **Configure System Audio**:
   - Open System Settings > Sound
   - Set the output device to "BlackHole 2ch"
   - Any audio played on your system will now be captured by the application

3. **Using System Audio Capture**:
   - Select "System Audio (BlackHole)" from the audio source dropdown
   - Start recording to capture system audio
   - Switch back to your regular output device to hear the audio

Note: When using system audio capture, make sure your system's audio is playing and BlackHole is properly configured as the output device.
