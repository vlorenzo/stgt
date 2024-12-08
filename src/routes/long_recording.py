"""Long recording-related routes."""

import os
import logging
import subprocess
import asyncio
from datetime import datetime
from uuid import uuid4
from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
from ..services.transcription import TranscriptionFactory
from ..services.text_enhancement import TextEnhancementFactory

# Create blueprint with the expected name
long_recording_bp = Blueprint('long_recording', __name__)
logger = logging.getLogger(__name__)

@long_recording_bp.route('/long-recording')
def index():
    """Render the long recording page."""
    return render_template('long_recording/index.html')

class RecordingSession:
    def __init__(self, session_id, config):
        self.session_id = session_id
        self.config = config
        self.segments = {}  # {segment_number: segment_info}
        self.start_time = datetime.now()
        self.status = 'recording'  # recording, processing, completed, error
        self.error = None
        self.combined_text = ""

class SegmentInfo:
    def __init__(self, segment_number, filepath):
        self.segment_number = segment_number
        self.filepath = filepath
        self.wav_path = None
        self.status = 'uploaded'  # uploaded, converting, transcribing, enhancing, completed, error
        self.transcription = None
        self.enhanced_text = None
        self.error = None

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', 'long_recordings')
        os.makedirs(self.upload_folder, exist_ok=True)

    def create_session(self, config):
        session_id = str(uuid4())
        session = RecordingSession(session_id, config)
        self.sessions[session_id] = session
        
        # Create session directory
        os.makedirs(os.path.join(self.upload_folder, session_id), exist_ok=True)
        logger.info(f"Created new session: {session_id}")
        logger.info(f"Session config: {config}")
        
        return session

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def get_segment_path(self, session_id, segment_number, extension):
        return os.path.join(
            self.upload_folder,
            session_id,
            f"{session_id}_{segment_number}.{extension}"
        )

session_manager = SessionManager()

def convert_to_wav(input_path):
    """Convert audio file to WAV format."""
    output_path = input_path.rsplit('.', 1)[0] + '.wav'
    try:
        # First try to get file info
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 
                    'stream=codec_name,codec_type', '-of', 
                    'default=noprint_wrappers=1', input_path]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        logger.info(f"FFprobe result: {probe_result.stdout}")

        if not probe_result.stdout.strip():
            logger.error("FFprobe could not detect audio stream")
            # Try direct conversion as fallback
            logger.info("Attempting direct conversion as fallback")
        
        # Construct FFmpeg command with more robust options
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if exists
            '-fflags', '+genpts',  # Generate presentation timestamps
            '-i', input_path,
            '-acodec', 'pcm_s16le',  # Output codec
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Number of channels
            '-af', 'aresample=async=1000',  # Handle async audio
            '-vn',  # No video
            '-hide_banner',  # Reduce output verbosity
            output_path
        ]
        
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"FFmpeg did not create output file: {output_path}")
            
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        raise

def process_segment(session_id, segment_number):
    """Process a single audio segment."""
    segment = None
    try:
        logger.info(f"Starting to process segment {segment_number} for session {session_id}")
        
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        segment = session.segments.get(segment_number)
        if not segment:
            raise ValueError(f"Segment {segment_number} not found in session {session_id}")

        # Log session configuration
        logger.info("Session configuration:")
        logger.info(f"Source Language: {session.config.get('source_language', 'not set')}")
        logger.info(f"Target Language: {session.config.get('target_language', 'not set')}")
        logger.info(f"Transcription Model: {session.config.get('transcription_model', 'not set')}")
        logger.info(f"Enhancement Model: {session.config.get('enhancement_model', 'not set')}")

        segment.status = 'converting'
        logger.info(f"Converting segment from {segment.filepath}")

        # Verify the audio file exists and has content
        if not os.path.exists(segment.filepath):
            raise ValueError(f"Audio file not found: {segment.filepath}")
            
        if os.path.getsize(segment.filepath) == 0:
            raise ValueError(f"Audio file is empty: {segment.filepath}")

        # Convert to WAV
        segment.wav_path = convert_to_wav(segment.filepath)
        logger.info(f"Converted to WAV: {segment.wav_path}")
        
        # Initialize transcription service based on config
        use_local_transcription = session.config['transcription_model'] == 'local'
        transcription_service = TranscriptionFactory.get_service(use_local=use_local_transcription)
        
        # Only perform transcription using source language
        segment.status = 'transcribing'
        source_lang = session.config['source_language']
        logger.info(f"Starting transcription with parameters:")
        logger.info(f"  - Source Language: {source_lang}")
        logger.info(f"  - Using {'local' if use_local_transcription else 'remote'} transcription service")
        
        transcription = transcription_service.transcribe(
            segment.wav_path,
            language=source_lang
        )
        
        # Validate transcription result
        if transcription is None:
            raise ValueError("Transcription service returned None")
            
        if not isinstance(transcription, str):
            raise ValueError(f"Invalid transcription type: {type(transcription)}")
            
        if not transcription.strip():
            raise ValueError("Transcription is empty")
            
        segment.transcription = transcription
        logger.info(f"Transcription completed. Result ({len(segment.transcription)} chars): {segment.transcription[:100]}...")
        
        segment.status = 'completed'
        logger.info(f"Successfully transcribed segment {segment_number}")
        
        # Update session status
        all_completed = all(
            seg.status == 'completed' and 
            seg.transcription is not None and 
            isinstance(seg.transcription, str) and 
            seg.transcription.strip()
            for seg in session.segments.values()
        )
        
        if all_completed:
            session.status = 'ready_for_enhancement'
            logger.info("All segments successfully transcribed and validated")
        
        return {"text": segment.transcription}

    except Exception as e:
        logger.error(f"Error processing segment: {str(e)}", exc_info=True)
        if segment:
            segment.status = 'error'
            segment.error = str(e)
        raise

def normalize_config(config):
    """Convert camelCase config keys to snake_case."""
    key_mapping = {
        'audioSource': 'audio_source',
        'targetLanguage': 'target_language',
        'outputType': 'output_type',
        'transcriptionModel': 'transcription_model',
        'enhancementModel': 'enhancement_model'
    }
    return {key_mapping.get(k, k): v for k, v in config.items()}

@long_recording_bp.route('/api/long-recording/create', methods=['POST'])
def create_session():
    """Create a new long recording session."""
    try:
        config = normalize_config(request.json)
        session = session_manager.create_session(config)
        return jsonify({"session_id": session.session_id})
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({"error": str(e)}), 500

@long_recording_bp.route('/api/long-recording/segment', methods=['POST'])
def process_segment_route():
    """Handle uploaded audio segment."""
    try:
        # Log all form data for debugging
        logger.info("Received segment upload request")
        logger.info(f"Form data: {request.form}")
        logger.info(f"Files: {request.files}")
        
        session_id = request.form.get('session_id')
        segment_number = int(request.form.get('segment_number'))
        audio_file = request.files.get('audio')
        
        if not all([session_id, segment_number, audio_file]):
            missing = []
            if not session_id: missing.append('session_id')
            if not segment_number: missing.append('segment_number')
            if not audio_file: missing.append('audio_file')
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
            
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Update session config with any new parameters
        form_config = {k: v for k, v in request.form.items() 
                      if k not in ['session_id', 'segment_number']}
        if form_config:
            session.config.update(form_config)
            logger.info(f"Updated session config: {session.config}")
            
        # Log file details
        content_type = audio_file.content_type
        logger.info(f"Audio file details - filename: {audio_file.filename}, content_type: {content_type}, size: {len(audio_file.read())} bytes")
        audio_file.seek(0)  # Reset file pointer after reading
        
        # Save the segment file
        filename = f"{session_id}_{segment_number}.webm"
        filepath = session_manager.get_segment_path(session_id, segment_number, 'webm')
        audio_file.save(filepath)
        
        # Verify file was saved and has content
        if not os.path.exists(filepath):
            return jsonify({'error': 'Failed to save audio file'}), 500
            
        file_size = os.path.getsize(filepath)
        logger.info(f"Segment file saved successfully. Size: {file_size} bytes")
        
        if file_size == 0:
            os.remove(filepath)
            return jsonify({'error': 'Uploaded file is empty'}), 400

        # Create segment info
        segment = SegmentInfo(segment_number, filepath)
        session.segments[segment_number] = segment
        logger.info(f"Stored segment {segment_number} for session {session_id}")

        # Process the segment
        try:
            result = process_segment(session_id, segment_number)
            return jsonify(result)
        except Exception as process_error:
            logger.error(f"Error during segment processing: {str(process_error)}")
            # Clean up the failed segment file
            try:
                os.remove(filepath)
                logger.info(f"Cleaned up failed segment file: {filepath}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up failed segment: {str(cleanup_error)}")
            raise process_error

    except Exception as save_error:
        logger.error(f"Error saving segment file: {str(save_error)}")
        raise save_error

@long_recording_bp.route('/api/long-recording/status/<session_id>', methods=['GET'])
def get_status(session_id):
    """Get the status of a recording session."""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        total_segments = len(session.segments)
        processed_segments = sum(
            1 for seg in session.segments.values() 
            if seg.status == 'completed'
        )
        
        return jsonify({
            'status': session.status,
            'total_segments': total_segments,
            'processed_segments': processed_segments,
            'progress_percentage': (processed_segments / total_segments * 100) if total_segments > 0 else 0,
            'combined_text': session.combined_text if session.status == 'completed' else None,
            'error': session.error
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@long_recording_bp.route('/api/long-recording/enhance/<session_id>', methods=['POST'])
def enhance_session(session_id):
    """Process all transcribed text after recording is complete."""
    try:
        logger.info(f"Starting enhancement for session {session_id}")
        
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Log enhancement configuration
        logger.info("Enhancement configuration:")
        logger.info(f"Source Language: {session.config.get('source_language', 'not set')}")
        logger.info(f"Target Language: {session.config.get('target_language', 'not set')}")
        logger.info(f"Output Type: {session.config.get('output_type', 'not set')}")
        logger.info(f"Enhancement Model: {session.config.get('enhancement_model', 'not set')}")
            
        # Collect all transcribed text in order
        segments = sorted(session.segments.values(), key=lambda x: x.segment_number)
        
        # Verify each segment's transcription
        valid_segments = []
        for seg in segments:
            logger.info(f"Checking segment {seg.segment_number}:")
            if seg.transcription is None:
                logger.warning(f"  - Segment {seg.segment_number} has no transcription")
                continue
            if not isinstance(seg.transcription, str):
                logger.warning(f"  - Segment {seg.segment_number} has invalid transcription type: {type(seg.transcription)}")
                continue
            if not seg.transcription.strip():
                logger.warning(f"  - Segment {seg.segment_number} has empty transcription")
                continue
                
            logger.info(f"  - Segment {seg.segment_number} is valid: {seg.transcription[:50]}...")
            valid_segments.append(seg)
        
        if not valid_segments:
            raise ValueError("No valid transcriptions found in any segment")
            
        logger.info(f"Found {len(valid_segments)} valid segments out of {len(segments)} total segments")
        
        # Combine only valid transcriptions
        combined_text = ' '.join(seg.transcription for seg in valid_segments)
        logger.info(f"Combined text length: {len(combined_text)} characters")
        
        if not combined_text.strip():
            raise ValueError("Combined transcription text is empty")
        
        # Perform enhancement and translation
        use_local_enhancement = session.config['enhancement_model'] == 'local'
        enhancement_service = TextEnhancementFactory.get_service(use_local=use_local_enhancement)
        
        target_lang = session.config['target_language']
        output_type = session.config['output_type']
        logger.info(f"Starting enhancement with parameters:")
        logger.info(f"  - Target Language: {target_lang}")
        logger.info(f"  - Output Type: {output_type}")
        logger.info(f"  - Using {'local' if use_local_enhancement else 'remote'} enhancement service")
        
        enhanced_text = enhancement_service.enhance(
            combined_text,
            target_language=target_lang,
            output_type=output_type
        )
        
        logger.info(f"Enhancement completed. Result ({len(enhanced_text)} chars): {enhanced_text[:100]}...")
        
        session.enhanced_text = enhanced_text
        session.status = 'completed'
        
        return jsonify({
            "enhanced_text": enhanced_text,
            "status": "completed",
            "segments_processed": {
                "total": len(segments),
                "valid": len(valid_segments)
            }
        })
        
    except Exception as e:
        logger.error(f"Error enhancing session: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e),
            "details": "Failed to process transcriptions. Some segments may have failed to transcribe properly."
        }), 500