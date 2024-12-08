"""Service for processing audio chunks in parallel while maintaining order."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from datetime import datetime
import os

from .chunk_management import ChunkManager
from .transcription import TranscriptionFactory

logger = logging.getLogger(__name__)

class ChunkProcessor:
    """Processes audio chunks in parallel while maintaining order."""
    
    def __init__(self, chunk_manager: ChunkManager):
        """Initialize the chunk processor.
        
        Args:
            chunk_manager: Instance of ChunkManager for accessing chunks
        """
        self.chunk_manager = chunk_manager
        self.max_workers = 3  # Number of parallel processing threads
        self.transcription_service = TranscriptionFactory.get_service(use_local=False)
        
    async def process_session(self, session_id: str) -> Dict:
        """Process all chunks in a session.
        
        Args:
            session_id: The session ID to process
            
        Returns:
            Dict containing processing results and status
        """
        try:
            logger.info(f"Starting processing for session {session_id}")
            session = self.chunk_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Update session status
            session['status'] = 'processing'
            
            # Get chunks and sort by sequence
            chunks = self.chunk_manager.get_unprocessed_chunks(session_id)
            chunks.sort(key=lambda x: x['metadata']['sequence'])
            
            logger.info(f"Processing {len(chunks)} chunks for session {session_id}")
            
            results = {}
            failed_chunks = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all chunks for processing
                future_to_chunk = {
                    executor.submit(self._process_chunk, chunk): chunk
                    for chunk in chunks
                }
                
                # Process results as they complete
                for future in as_completed(future_to_chunk):
                    chunk = future_to_chunk[future]
                    try:
                        result = future.result()
                        sequence = chunk['metadata']['sequence']
                        results[sequence] = result
                        logger.info(f"Processed chunk {sequence} for session {session_id}")
                        
                        # Update chunk status
                        self.chunk_manager.mark_chunk_processed(
                            session_id,
                            chunk['id'],
                            result
                        )
                        
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk['id']}: {str(e)}")
                        failed_chunks.append({
                            'chunk_id': chunk['id'],
                            'error': str(e)
                        })
            
            # Check if any chunks failed
            if failed_chunks:
                logger.error(f"Some chunks failed processing in session {session_id}")
                session['status'] = 'partial_failure'
                return {
                    'status': 'partial_failure',
                    'failed_chunks': failed_chunks,
                    'processed_chunks': len(results)
                }
            
            # Assemble final result in correct order
            final_result = self._assemble_results(results)
            
            # Update session status
            session['status'] = 'completed'
            session['completed_at'] = datetime.utcnow()
            session['result'] = final_result
            
            logger.info(f"Completed processing session {session_id}")
            
            return {
                'status': 'success',
                'result': final_result,
                'processed_chunks': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error processing session {session_id}: {str(e)}")
            if session:
                session['status'] = 'failed'
            raise
    
    def _process_chunk(self, chunk: Dict) -> Dict:
        """Process a single audio chunk.
        
        Args:
            chunk: The chunk information dictionary
            
        Returns:
            Dict containing processing results
        """
        try:
            logger.debug(f"Processing chunk {chunk['id']}")
            
            # Transcribe the audio chunk
            transcript = self.transcription_service.transcribe(
                chunk['path'],
                "it"  # TODO: Make language configurable
            )
            
            return {
                'transcript': transcript,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk['id']}: {str(e)}")
            raise
    
    def _assemble_results(self, results: Dict) -> Dict:
        """Assemble final results from processed chunks.
        
        Args:
            results: Dictionary of results keyed by sequence number
            
        Returns:
            Dict containing assembled results
        """
        try:
            # Sort chunks by sequence number
            sequences = sorted(results.keys())
            
            # Combine transcripts
            combined_transcript = []
            for seq in sequences:
                combined_transcript.append(results[seq]['transcript'])
            
            return {
                'transcript': ' '.join(combined_transcript),
                'chunk_count': len(sequences),
                'completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error assembling results: {str(e)}")
            raise 