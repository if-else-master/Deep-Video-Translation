import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import soundfile as sf

def main():
    config = XttsConfig()
    config.load_json("app/XTTS-v2/config.json")
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir="app/XTTS-v2", eval=True)
    device = torch.device("cpu")
    model.to(device)

    speaker_wav = "app/XTTS-v2/samples/zh-cn-sample.wav"
    text = "It took me quite a long time to develop a voice and now that I have it I am not going to be silent."

    outputs = model.synthesize(
        text,
        config,
        speaker_wav=speaker_wav,
        gpt_cond_len=3,
        language="en",
    )

    audio = outputs[0] if isinstance(outputs, (list, tuple)) else outputs

    sf.write("output.wav", audio, samplerate=config.audio["sample_rate"])
    print("已輸出音訊檔 output.wav")

if __name__ == "__main__":
    main()
