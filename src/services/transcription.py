"""Transcription services for audio processing."""

import os
import logging
from abc import ABC, abstractmethod
import torch
import whisper
from openai import OpenAI
from typing import Optional
from ..utils.system import check_ffmpeg

logger = logging.getLogger(__name__)

class TranscriptionService(ABC):
    """Abstract base class for transcription services."""
    
    @abstractmethod
    def transcribe(self, audio_file_path: str, language: str) -> str:
        """Transcribe audio file to text."""
        pass

class OpenAITranscriptionService(TranscriptionService):
    """OpenAI's Whisper API-based transcription service."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def transcribe(self, audio_file_path: str, language: str) -> str:
        """Transcribe audio using OpenAI's Whisper API."""
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
        return transcript.text

class LocalWhisperTranscriptionService(TranscriptionService):
    """Local Whisper model-based transcription service."""
    
    def __init__(self):
        """Initialize the local Whisper model."""
        if not check_ffmpeg():
            raise RuntimeError(
                "ffmpeg is not installed. Please install ffmpeg first:\n"
                "- On macOS: brew install ffmpeg\n"
                "- On Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "- On Windows: Download from https://ffmpeg.org/download.html"
            )
        
        logger.info("Loading Whisper model on CPU")
        self.model = whisper.load_model("turbo") # I need to choose the whisper model between base, small, medium, large and turbo.
    
    def transcribe(self, audio_file_path: str, language: str) -> str:
        """Transcribe audio using the local Whisper model."""
        try:
            result = self.model.transcribe(
                audio_file_path,
                language=language
            )
            return result["text"]
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise

class TranscriptionFactory:
    """Factory for creating transcription services."""
    
    _openai_instance: Optional[OpenAITranscriptionService] = None
    _local_instance: Optional[LocalWhisperTranscriptionService] = None
    
    @classmethod
    def get_service(cls, use_local: bool = False) -> TranscriptionService:
        """Get a transcription service instance."""
        if use_local:
            if cls._local_instance is None:
                cls._local_instance = LocalWhisperTranscriptionService()
            return cls._local_instance
        else:
            if cls._openai_instance is None:
                cls._openai_instance = OpenAITranscriptionService()
            return cls._openai_instance 