import os
import tempfile
from flask import Flask, render_template, request, jsonify
import pyaudio
import wave
import openai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files['audio']
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        
    try:
        with open(temp_audio.name, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        
        analysis = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes text and rewrites it to be correct and brief for an email message content."},
                {"role": "user", "content": f"Please analyze and rewrite the following text to be correct and brief for an email message content: {transcript['text']}"}
            ]
        )
        
        return jsonify({
            "transcript": transcript['text'],
            "analysis": analysis.choices[0].message['content']
        })
    finally:
        os.unlink(temp_audio.name)

if __name__ == '__main__':
    app.run(debug=True)
