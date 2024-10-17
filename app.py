import os
import tempfile
import json
from flask import Flask, render_template, request, jsonify
import pyaudio
import wave
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files['audio']
    language_json = request.form.get('language', '{"code": "it", "label": "Italian"}')
    language = json.loads(language_json)
    
    transcription_time = datetime.now().strftime("%H:%M:%S")
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        
    try:
        with open(temp_audio.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="it"
            )
        
        system_prompt = f"You are a helpful assistant that analyzes text and rewrites it to be correct and brief as for an email like message content. Respond in {language['label']}."
        user_prompt = f"Please analyze and rewrite the following text in {language['label']}: {transcript.text}"
        
        analysis = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        analysis_time = datetime.now().strftime("%H:%M:%S")
        
        return jsonify({
            "transcript": transcript.text,
            "transcription_time": transcription_time,
            "analysis": analysis.choices[0].message.content,
            "analysis_time": analysis_time
        })
    finally:
        os.unlink(temp_audio.name)

if __name__ == '__main__':
    app.run(debug=True)
