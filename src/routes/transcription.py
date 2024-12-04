"""Transcription-related routes."""

import os
import tempfile
import json
import logging
from datetime import datetime
import time
from flask import Blueprint, request, jsonify, render_template
from ..services.transcription import TranscriptionFactory
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client for text processing
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create blueprint
transcription_bp = Blueprint('transcription', __name__)

@transcription_bp.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@transcription_bp.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle audio transcription and translation requests."""
    start_time = time.time()
    logger.info("=== New Transcription Request ===")
    
    # Get request parameters
    audio_file = request.files['audio']
    language_json = request.form.get('language', '{"code": "it", "label": "Italian"}')
    language = json.loads(language_json)
    output_type = request.form.get('output_type', 'general')
    use_local_model = request.form.get('use_local_model', 'false').lower() == 'true'
    
    transcription_time = datetime.now().strftime("%H:%M:%S")
    logger.debug(f"Request parameters: language={language}, output_type={output_type}, use_local_model={use_local_model}")
    
    # Save the audio file temporarily
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        logger.debug(f"Saved temporary audio file: {temp_audio.name}")
        
    try:
        # Step 1: Transcribe audio
        step_start_time = time.time()
        model_type = "Local Whisper" if use_local_model else "OpenAI API"
        logger.info(f"Starting transcription using {model_type}")
        
        transcription_service = TranscriptionFactory.get_service(use_local=use_local_model)
        transcript_text = transcription_service.transcribe(temp_audio.name, "it")
        
        step_duration = time.time() - step_start_time
        logger.info(f"Transcription completed in {step_duration:.2f}s using {model_type}")
        logger.debug(f"Transcription result: {transcript_text}")

        # Step 2: Translate and improve the text
        step_start_time = time.time()
        logger.info("Starting text enhancement with GPT")
        
        system_prompt = f"""
        You are a helpful assistant that translates Italian text to {language['label']} 
        and improves it to be correct and brief for a {output_type}. 
        Adapt the style and tone to be appropriate for the specified output type.
        Just output the translated and improved text.
        """
        
        user_prompt = f"""
        Please translate the following Italian text to {language['label']} and format it as a {output_type}:

        {transcript_text}
        """
        
        analysis = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        step_duration = time.time() - step_start_time
        logger.info(f"Text enhancement completed in {step_duration:.2f}s")
        logger.debug(f"Enhanced text: {analysis.choices[0].message.content}")
        
        analysis_time = datetime.now().strftime("%H:%M:%S")
        total_duration = time.time() - start_time
        logger.info(f"=== Request completed in {total_duration:.2f}s ===")

        # Return the results
        return jsonify({
            "transcript": transcript_text,
            "transcription_time": transcription_time,
            "analysis": analysis.choices[0].message.content,
            "analysis_time": analysis_time
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        error_message = str(e)
        if "ffmpeg" in error_message.lower():
            error_message = (
                "ffmpeg is not installed. Please install ffmpeg first:\n"
                "- On macOS: brew install ffmpeg\n"
                "- On Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "- On Windows: Download from https://ffmpeg.org/download.html"
            )
        return jsonify({'error': error_message}), 500
        
    finally:
        # Clean up the temporary audio file
        os.unlink(temp_audio.name)
        logger.debug("Cleaned up temporary audio file")