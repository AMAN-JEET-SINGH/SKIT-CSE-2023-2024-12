import subprocess
import shutil
if not shutil.which("ffmpeg"):
    raise EnvironmentError("ffmpeg not found. Please install it and add to PATH.")

def extract_audio_ffmpeg(video_path, output_audio="temp_audio.wav"):
    """Using ffmpeg directly (faster)"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # WAV codec
        '-ar', '16000',  # 16kHz
        '-ac', '1',  # Mono
        output_audio,
        '-y'  # Overwrite
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e.stderr.decode()}")
    return output_audio


if __name__ == "__main__":
    extract_audio_ffmpeg("S20230010071_SE_VideoResume.mp4")