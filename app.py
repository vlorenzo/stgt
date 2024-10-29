import os
import tempfile
import json
from flask import Flask, render_template, request, jsonify
import pyaudio
import wave
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import time
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Handle audio transcription and translation requests.
    This function receives an audio file, transcribes it from Italian,
    then translates and improves the text to the specified target language and output type.
    """
    app.logger.info("Received transcription request")
    start_time = time.time()

    # Get audio file, target language, and output type from the request
    audio_file = request.files['audio']
    language_json = request.form.get('language', '{"code": "it", "label": "Italian"}')
    language = json.loads(language_json)
    output_type = request.form.get('output_type', 'general')
    
    transcription_time = datetime.now().strftime("%H:%M:%S")
    
    # Save the audio file temporarily
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        
    try:
        # Step 1: Transcribe audio (always from Italian)
        app.logger.debug("Starting OpenAI API call for transcription")
        api_start_time = time.time()
        with open(temp_audio.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="it"  # Always use Italian for input
            )
        api_end_time = time.time()
        app.logger.info(f"OpenAI API transcription completed in {api_end_time - api_start_time:.2f} seconds")

        # Step 2: Translate and improve the transcribed text
        system_prompt = f"""
        You are a helpful assistant that translates Italian text to {language['label']} 
        and improves it to be correct and brief for a {output_type}. 
        Adapt the style and tone to be appropriate for the specified output type.
        Just output the translated and improved text.
        """
        user_prompt = f"""
        Please translate the following Italian text to {language['label']} and format it as a {output_type}:

        {transcript.text}
        """
        
        app.logger.debug("Starting OpenAI API call for text processing")
        api_start_time = time.time()
        analysis = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        api_end_time = time.time()
        app.logger.info(f"OpenAI API text processing completed in {api_end_time - api_start_time:.2f} seconds")
        
        analysis_time = datetime.now().strftime("%H:%M:%S")
        
        end_time = time.time()
        app.logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")

        # Return the results
        return jsonify({
            "transcript": transcript.text,
            "transcription_time": transcription_time,
            "analysis": analysis.choices[0].message.content,
            "analysis_time": analysis_time
        })
    except Exception as e:
        app.logger.error(f"Error processing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary audio file
        os.unlink(temp_audio.name)

# The /record route is commented out as it's not being used in the current implementation
'''
@app.route('/record', methods=['POST'])
def record():
    """
    Handle audio recording requests.
    This function receives an audio file, saves it, transcribes it,
    and then processes the transcription to make it suitable for an email.
    """
    app.logger.info("Received audio recording request")
    start_time = time.time()
    
    if 'audio' not in request.files:
        app.logger.error("No audio file received")
        return jsonify({'error': 'No audio file received'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        app.logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    if audio_file:
        # Save the audio file
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        app.logger.info(f"Audio file saved: {filepath}")

        try:
            # Transcribe the audio
            app.logger.debug("Starting OpenAI API call for transcription")
            api_start_time = time.time()
            with open(filepath, "rb") as file:
                transcript = openai.Audio.transcribe("whisper-1", file)
            api_end_time = time.time()
            app.logger.info(f"OpenAI API transcription completed in {api_end_time - api_start_time:.2f} seconds")

            # Process the transcription
            app.logger.debug("Starting OpenAI API call for text processing")
            api_start_time = time.time()
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """
                    You are a helpful assistant that rewrites text to be correct 
                    and brief for an email message content.
                    """},
                    {"role": "user", "content": f"""
                    Please rewrite the following text to be correct and brief 
                    for an email message content:

                    {transcript['text']}
                    """}
                ]
            )
            api_end_time = time.time()
            app.logger.info(f"OpenAI API text processing completed in {api_end_time - api_start_time:.2f} seconds")

            processed_text = response['choices'][0]['message']['content']
            
            end_time = time.time()
            app.logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")
            
            return jsonify({'transcript': transcript['text'], 'processed_text': processed_text})
        except Exception as e:
            app.logger.error(f"Error processing audio: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    app.logger.error("Unknown error occurred")
    return jsonify({'error': 'Unknown error occurred'}), 500
'''

if __name__ == '__main__':
    app.logger.info("Starting the application")
    app.run(debug=True)
