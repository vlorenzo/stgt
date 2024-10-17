# STGT (Speech to Good Text)

STGT is an AI-powered application that allows users to record audio, transcribe it, and receive an AI-generated analysis of the content. It supports multiple languages and provides a user-friendly web interface.

## Core Features

- Audio recording through the browser
- Transcription of audio using OpenAI's Whisper model
- AI-powered analysis and rewriting of the transcribed text using GPT-4
- Support for multiple languages
- Real-time display of transcription and analysis results
- Copy-to-clipboard functionality for easy sharing

## Prerequisites

- Python 3.7 or higher
- OpenAI API key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/vlorenzo/stgt.git
   cd stgt
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

### For macOS and Linux users:

1. Open a terminal and navigate to the project directory.
2. Run the following command to start the application:
   ```
   python app.py
   ```
3. Open a web browser and go to `http://localhost:5000`.

### For Windows users:

1. Open Command Prompt and navigate to the project directory.
2. Run the following command to start the application:
   ```
   python app.py
   ```
3. Open a web browser and go to `http://localhost:5000`.

## How to Use

1. Select your desired language from the dropdown menu.
2. Click the "Start Recording" button and speak into your microphone.
3. Click "Stop Recording" when you're finished speaking.
4. Wait for the transcription and analysis to complete.
5. View the transcription and AI-generated analysis.
6. Use the copy button to easily copy the analysis to your clipboard.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the [STGT repository](https://github.com/vlorenzo/stgt).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
