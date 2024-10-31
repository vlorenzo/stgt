# STGT (Speech to Good Text)

STGT is an AI-powered application that allows users to record audio, transcribe it, and receive an improved version of the text suitable for various output types. It supports multiple languages and provides a user-friendly web interface with secure HTTPS connection.

## Core Features

- Audio recording through the browser
- Transcription of audio using OpenAI's speech-to-text service
- AI-powered rewriting of the transcribed text to improve quality and brevity for various output types
- Optional translation to a target language
- Support for multiple languages
- Real-time display of transcription and improved text results
- Copy-to-clipboard functionality for easy sharing
- Secure HTTPS connection

## Prerequisites

- Python 3.7 or higher
- OpenAI API key
- OpenSSL (for generating SSL certificate)

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

4. Generate a self-signed SSL certificate (for development purposes only):
   ```
   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
   ```
   When prompted for "Common Name", enter `localhost` or your local IP address.

## Usage

1. Open a terminal and navigate to the project directory.
2. Run the following command to start the application:
   ```
   python app.py
   ```
3. Open a web browser and go to `https://localhost:5001` or `https://your.local.ip.address:5001`.
   Note: Your browser may warn you about the self-signed certificate. You'll need to proceed anyway (this is safe for local development).

## How to Use

1. Select your desired output language from the dropdown menu.
2. Choose the output type (email, WhatsApp message, AI model prompt, or general text).
3. Click the "Start Recording" button and speak into your microphone.
4. Click "Stop Recording" when you're finished speaking.
5. Wait for the transcription and text improvement to complete.
6. View the original Italian transcription and the improved text in the selected language and format.
7. Use the copy button to easily copy the improved text to your clipboard.

## Troubleshooting

- If you encounter issues with microphone access, ensure you're using a modern browser and that you've granted the necessary permissions.
- If you're using Chrome and having issues with the self-signed certificate, you can enable insecure localhost by visiting `chrome://flags/#allow-insecure-localhost` and enabling the flag.

## Security Note

The provided SSL setup is for development purposes only. For production use, obtain a proper SSL certificate from a trusted Certificate Authority.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the [STGT repository](https://github.com/vlorenzo/stgt).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
