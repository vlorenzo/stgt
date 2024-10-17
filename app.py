import os
import tempfile
from flask import Flask, render_template, request, jsonify
import pyaudio
import wave
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
            transcript = client.audio.transcriptions.create(
                model="whisper-1", #"large-v3-turbo", 
                file=audio_file,
                language="it"
            )
        
        analysis = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes text and rewrites it to be correct and brief for an email message content."},
                {"role": "user", "content": f"Please analyze and rewrite the following text to be correct and brief for an email message content and preserve the original language: {transcript.text}"}
            ]
        )
        
        return jsonify({
            "transcript": transcript.text,
            "analysis": analysis.choices[0].message.content
        })
    finally:
        os.unlink(temp_audio.name)

if __name__ == '__main__':
    app.run(debug=True)
