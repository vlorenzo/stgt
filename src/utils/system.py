"""System utility functions."""

import shutil

def check_ffmpeg() -> bool:
    """Check if ffmpeg is installed and accessible.
    
    Returns:
        bool: True if ffmpeg is available, False otherwise.
    """
    return shutil.which('ffmpeg') is not None 