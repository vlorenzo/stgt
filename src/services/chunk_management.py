"""Service for managing audio chunks in long recordings."""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ChunkManager:
    """Manages the storage and tracking of audio chunks for long recordings."""
    
    def __init__(self, base_storage_path: str):
        """Initialize the chunk manager.
        
        Args:
            base_storage_path: Base directory for storing audio chunks
        """
        self.base_path = base_storage_path
        self.active_sessions: Dict[str, Dict] = {}
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(f"Initialized ChunkManager with storage path: {self.base_path}")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
    
    def create_session(self) -> str:
        """Create a new recording session.
        
        Returns:
            str: The session ID
        """
        session_id = self._generate_session_id()
        session_path = os.path.join(self.base_path, session_id)
        os.makedirs(session_path)
        
        self.active_sessions[session_id] = {
            'created_at': datetime.utcnow(),
            'chunks': [],
            'status': 'recording',
            'processed_chunks': 0,
            'total_chunks': 0,
            'current_phase': 'recording',
            'errors': []
        }
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def store_chunk(self, session_id: str, chunk_data, metadata: Dict) -> str:
        """Store a new chunk for the session.
        
        Args:
            session_id: The session ID
            chunk_data: The audio chunk data
            metadata: Chunk metadata (sequence, timestamp, etc.)
            
        Returns:
            str: The chunk ID
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        chunk_id = f"{session_id}_{metadata['sequence']}"
        chunk_path = os.path.join(self.base_path, session_id, f"{chunk_id}.webm")
        
        # Store the chunk
        with open(chunk_path, 'wb') as f:
            chunk_data.save(f)
        
        # Update session metadata
        chunk_info = {
            'id': chunk_id,
            'path': chunk_path,
            'metadata': metadata,
            'stored_at': datetime.utcnow(),
            'processed': False,
            'processing_attempts': 0,
            'result': None,
            'error': None
        }
        
        session = self.active_sessions[session_id]
        session['chunks'].append(chunk_info)
        session['total_chunks'] = len(session['chunks'])
        
        logger.info(f"Stored chunk {chunk_id} for session {session_id}")
        return chunk_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict: Session information or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def get_chunk(self, session_id: str, chunk_id: str) -> Optional[Dict]:
        """Get chunk information.
        
        Args:
            session_id: The session ID
            chunk_id: The chunk ID
            
        Returns:
            Dict: Chunk information or None if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        for chunk in session['chunks']:
            if chunk['id'] == chunk_id:
                return chunk
        
        return None
    
    def mark_chunk_processed(self, session_id: str, chunk_id: str, result: Dict = None):
        """Mark a chunk as processed.
        
        Args:
            session_id: The session ID
            chunk_id: The chunk ID
            result: Processing result data
        """
        chunk = self.get_chunk(session_id, chunk_id)
        if chunk:
            chunk['processed'] = True
            chunk['processed_at'] = datetime.utcnow()
            chunk['result'] = result
            
            # Update session progress
            session = self.active_sessions[session_id]
            session['processed_chunks'] += 1
            
            # Update phase if all chunks are processed
            if session['processed_chunks'] == session['total_chunks']:
                session['current_phase'] = 'completed'
            
            logger.info(f"Marked chunk {chunk_id} as processed ({session['processed_chunks']}/{session['total_chunks']})")
    
    def mark_chunk_failed(self, session_id: str, chunk_id: str, error: str):
        """Mark a chunk as failed.
        
        Args:
            session_id: The session ID
            chunk_id: The chunk ID
            error: Error message
        """
        chunk = self.get_chunk(session_id, chunk_id)
        if chunk:
            chunk['error'] = error
            chunk['processing_attempts'] += 1
            
            # Add to session errors
            session = self.active_sessions[session_id]
            session['errors'].append({
                'chunk_id': chunk_id,
                'error': error,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.error(f"Marked chunk {chunk_id} as failed: {error}")
    
    def get_session_progress(self, session_id: str) -> Dict:
        """Get detailed progress information for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict: Progress information
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            'status': session['status'],
            'current_phase': session['current_phase'],
            'processed_chunks': session['processed_chunks'],
            'total_chunks': session['total_chunks'],
            'progress_percentage': (session['processed_chunks'] / max(session['total_chunks'], 1)) * 100,
            'errors': session['errors'],
            'created_at': session['created_at'].isoformat(),
            'duration': (datetime.utcnow() - session['created_at']).total_seconds()
        }
    
    def cleanup_session(self, session_id: str):
        """Clean up a session's temporary files.
        
        Args:
            session_id: The session ID
        """
        session_path = os.path.join(self.base_path, session_id)
        if os.path.exists(session_path):
            for chunk in self.active_sessions[session_id]['chunks']:
                if os.path.exists(chunk['path']):
                    os.remove(chunk['path'])
            os.rmdir(session_path)
        
        del self.active_sessions[session_id]
        logger.info(f"Cleaned up session: {session_id}")
    
    def get_unprocessed_chunks(self, session_id: str) -> List[Dict]:
        """Get all unprocessed chunks for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List[Dict]: List of unprocessed chunks
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return []
        
        return [chunk for chunk in session['chunks'] 
                if not chunk.get('processed') and 
                chunk.get('processing_attempts', 0) < 3]  # Allow up to 3 retry attempts 