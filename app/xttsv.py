import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import soundfile as sf
import numpy as np
import os

def xttsv(text, output_path="output.wav"):
    config = XttsConfig()
    config.load_json("app/XTTS-v2/config.json")
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir="app/XTTS-v2", eval=True)
    device = torch.device("cpu")
    model.to(device)

    speaker_wav = "app/XTTS-v2/samples/zh-cn-sample.wav"

    outputs = model.synthesize(
        text,
        config,
        speaker_wav=speaker_wav,
        gpt_cond_len=3,
        language="en",
    )

    # 从字典中获取音频数据
    if isinstance(outputs, dict):
        audio = outputs.get("wav", None)
        if audio is None:
            raise ValueError("无法在模型输出中找到音频数据")
    else:
        audio = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
    
    # 确保音频数据是正确的格式
    if isinstance(audio, torch.Tensor):
        audio = audio.cpu().numpy()
    
    # 确保音频数据是二维的
    if len(audio.shape) == 1:
        audio = audio.reshape(-1, 1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    sf.write(output_path, audio, samplerate=config.audio["sample_rate"])
    print(f"已輸出音訊檔 {output_path}")
    
    return output_path

# if __name__ == "__main__":
#     main()
