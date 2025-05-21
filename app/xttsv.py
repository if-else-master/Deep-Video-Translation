from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import torch
import os

# 設置 CPU 執行緒數量以提高性能
os.environ["OMP_NUM_THREADS"] = "8"  # 調整為您的 M4 核心數或更低一些
os.environ["MKL_NUM_THREADS"] = "8"  # 同上
torch.set_num_threads(8)  # 同上

# 可選：啟用 Intel MKL（如果已安裝）的動態調整
os.environ["MKL_DYNAMIC"] = "TRUE"

config = XttsConfig()
config.load_json("app/XTTS-v2/config.json")

# 修改配置以適應 CPU 模式
config.model_args.decoder_use_fp16 = False  # 禁用 FP16 避免兼容性問題
config.model_args.encoder_use_fp16 = False  # 禁用 FP16 避免兼容性問題

model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="app/XTTS-v2", eval=True)

# 明確使用 CPU
device = torch.device("cpu")
model.to(device)

# 可選：降低批次大小以減少內存使用
batch_size = 1

# 可選：如果內存允許，預加載一些模型數據
# model.encoder.gpt.preload_stats = True

print("使用優化的 CPU 模式")

outputs = model.synthesize(
    "It took me quite a long time to develop a voice and now that I have it I am not going to be silent.",
    config,
    speaker_wav="./samp/567.wav",
    gpt_cond_len=3,
    language="en",
    # 降低精度來提高速度
    use_fp16=False,
    # 如果有此參數則設置
    temperature=0.7,  # 降低溫度可能會加快生成速度
)