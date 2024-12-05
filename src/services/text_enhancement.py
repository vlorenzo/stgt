"""Text enhancement services for processing transcribed text."""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class TextEnhancementService(ABC):
    """Abstract base class for text enhancement services."""
    
    @abstractmethod
    def enhance(self, text: str, target_language: str, output_type: str) -> str:
        """Enhance and translate text to target language and format.
        
        Args:
            text: The input text to enhance
            target_language: The target language for translation
            output_type: The desired output format (email, whatsapp, etc.)
            
        Returns:
            Enhanced and translated text
        """
        pass

class OpenAIEnhancementService(TextEnhancementService):
    """OpenAI GPT-based text enhancement service."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def enhance(self, text: str, target_language: str, output_type: str) -> str:
        """Enhance text using OpenAI's GPT model."""
        system_prompt = f"""
        You are a helpful assistant that translates text to {target_language} 
        and improves it to be correct and brief for a {output_type}. 
        Adapt the style and tone to be appropriate for the specified output type.
        Just output the translated and improved text.
        """
        
        user_prompt = f"""
        Please translate the following text to {target_language} and format it as a {output_type}:

        {text}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.choices[0].message.content

class OllamaEnhancementService(TextEnhancementService):
    """Local Llama-based text enhancement service using Ollama."""
    
    def __init__(self):
        """Initialize the Ollama client."""
        self.api_base = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2:3.2")
        
        # Test connection and model availability
        self._check_model_availability()
    
    def _check_model_availability(self):
        """Check if the model is available in Ollama."""
        try:
            response = requests.get(f"{self.api_base}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                if not any(m["name"] == self.model for m in models):
                    logger.warning(f"Model {self.model} not found in Ollama. Please pull it first.")
            else:
                logger.error("Failed to get model list from Ollama")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
    
    def enhance(self, text: str, target_language: str, output_type: str) -> str:
        """Enhance text using local Llama model via Ollama."""
        prompt = f"""
        Translate and enhance the following text to {target_language}.
        Format it as a {output_type}, making it correct and brief.
        Adapt the style and tone to be appropriate for a {output_type}.
        Only respond with the translated and enhanced text.

        Text to enhance:
        {text}
        """
        
        try:
            response = requests.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                raise RuntimeError("Failed to get response from Ollama")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {str(e)}")
            raise RuntimeError(f"Failed to communicate with Ollama: {str(e)}")

class TextEnhancementFactory:
    """Factory for creating text enhancement services."""
    
    _openai_instance: Optional[OpenAIEnhancementService] = None
    _ollama_instance: Optional[OllamaEnhancementService] = None
    
    @classmethod
    def get_service(cls, use_local: bool = False) -> TextEnhancementService:
        """Get a text enhancement service instance.
        
        Args:
            use_local: Whether to use local Ollama service (True) or OpenAI (False)
            
        Returns:
            An instance of TextEnhancementService
        """
        if use_local:
            if cls._ollama_instance is None:
                cls._ollama_instance = OllamaEnhancementService()
            return cls._ollama_instance
        else:
            if cls._openai_instance is None:
                cls._openai_instance = OpenAIEnhancementService()
            return cls._openai_instance 