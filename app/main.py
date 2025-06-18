from app.txtvoice import voice
from app.xttsv import xttsv

voice_text = voice("../audio_files/111.mp4")

xttsv(voice_text)