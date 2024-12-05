"""Transcription-related routes."""

import os
import tempfile
import json
import logging
from datetime import datetime
import time
import wave
from mutagen import File
from flask import Blueprint, request, jsonify, render_template
from ..services.transcription import TranscriptionFactory
from ..services.text_enhancement import TextEnhancementFactory

# Configure logging
logger = logging.getLogger(__name__)

def get_audio_duration(file_path: str) -> float:
    """Get the duration of an audio file in seconds.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Duration in seconds
    """
    try:
        audio = File(file_path)
        if audio is not None and hasattr(audio.info, 'length'):
            return audio.info.length
        
        # Fallback to wave for WAV files
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate)
                
        return 0.0
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {str(e)}")
        return 0.0

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
    use_local_enhancement = request.form.get('use_local_enhancement', 'false').lower() == 'true'
    
    transcription_time = datetime.now().strftime("%H:%M:%S")
    logger.debug(
        f"Request parameters: language={language}, output_type={output_type}, "
        f"use_local_model={use_local_model}, use_local_enhancement={use_local_enhancement}"
    )
    
    # Save the audio file temporarily
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        logger.debug(f"Saved temporary audio file: {temp_audio.name}")
        
        # Get and log audio duration
        duration = get_audio_duration(temp_audio.name)
        duration_msg = f"Audio duration: {duration:.2f} seconds"
        logger.info(duration_msg)
        
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
        enhancement_type = "Local Llama" if use_local_enhancement else "OpenAI GPT"
        logger.info(f"Starting text enhancement with {enhancement_type}")
        
        enhancement_service = TextEnhancementFactory.get_service(use_local=use_local_enhancement)
        enhanced_text = enhancement_service.enhance(
            text=transcript_text,
            target_language=language['label'],
            output_type=output_type
        )
        
        step_duration = time.time() - step_start_time
        logger.info(f"Text enhancement completed in {step_duration:.2f}s using {enhancement_type}")
        logger.debug(f"Enhanced text: {enhanced_text}")

        analysis_time = datetime.now().strftime("%H:%M:%S")
        total_duration = time.time() - start_time
        logger.info(f"=== Request completed in {total_duration:.2f}s ===")

        # Return the results
        return jsonify({
            "transcript": transcript_text,
            "transcription_time": transcription_time,
            "analysis": enhanced_text,
            "analysis_time": analysis_time,
            "audio_duration": f"{duration:.2f}"
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
        logger.debug(f"Cleaned up temporary audio file {temp_audio.name}")