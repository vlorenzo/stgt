# STGT - Speech To Generative Text

A Flask-based web application that transcribes speech to text and enhances it using AI. The application supports both OpenAI's Whisper API and local Whisper model for transcription, with special optimizations for macOS.

## Features

- Real-time audio recording through web browser
- Dual transcription options:
  - OpenAI Whisper API (requires API key, faster)
  - Local Whisper model (offline capable, no API costs)
- Multiple Whisper model options (base, small, medium, large, turbo)
- Text enhancement using GPT-4
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
- OpenAI API key (for OpenAI services)

## Installation

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install ffmpeg** (required for local Whisper model):
   ```bash
   brew install ffmpeg
   ```

3. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/stgt.git
   cd stgt
   ```

4. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

7. **Generate SSL certificate** (required for microphone access):
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
