from os import listdir, path
import numpy as np
import scipy, cv2, os, sys, argparse
import audio
import json, subprocess, random, string
from tqdm import tqdm
from glob import glob
import torch
from face_detection import FaceAlignment, LandmarksType
from models import Wav2Lip
import platform

parser = argparse.ArgumentParser(description='Inference code to lip-sync videos in the wild using Wav2Lip models')

parser.add_argument('--checkpoint_path', type=str, 
					help='Name of saved checkpoint to load weights from', default='app/Wav2Lip/checkpoints/wav2lip.pth')

parser.add_argument('--face', type=str, 
					help='Filepath of video/image that contains faces to use', default='app/Wav2Lip/exc/111.mp4')
parser.add_argument('--audio', type=str, 
					help='Filepath of video/audio file to use as raw audio source', default='app/Wav2Lip/exc/666.wav')
parser.add_argument('--outfile', type=str, help='Video path to save result. See default for an e.g.', 
								default='app/Wav2Lip/results/result_voice6.mp4')


parser.add_argument('--static', type=bool, 
					help='If True, then use only first video frame for inference', default=False)
parser.add_argument('--fps', type=float, help='Can be specified only if input is a static image (default: 25)', 
					default=25., required=False)

parser.add_argument('--pads', nargs='+', type=int, default=[0, 10, 0, 0], 
					help='Padding (top, bottom, left, right). Please adjust to include chin at least')

parser.add_argument('--face_det_batch_size', type=int, 
					help='Batch size for face detection', default=4)
parser.add_argument('--wav2lip_batch_size', type=int, help='Batch size for Wav2Lip model(s)', default=32)

parser.add_argument('--resize_factor', default=2, type=int, 
			help='Reduce the resolution by this factor. Sometimes, best results are obtained at 480p or 720p')

parser.add_argument('--crop', nargs='+', type=int, default=[0, -1, 0, -1], 
					help='Crop video to a smaller region (top, bottom, left, right). Applied after resize_factor and rotate arg. ' 
					'Useful if multiple face present. -1 implies the value will be auto-inferred based on height, width')

parser.add_argument('--box', nargs='+', type=int, default=[-1, -1, -1, -1], 
					help='Specify a constant bounding box for the face. Use only as a last resort if the face is not detected.'
					'Also, might work only if the face is not moving around much. Syntax: (top, bottom, left, right).')

parser.add_argument('--rotate', default=False, action='store_true',
					help='Sometimes videos taken from a phone can be flipped 90deg. If true, will flip video right by 90deg.'
					'Use if you get a flipped result, despite feeding a normal looking video')

parser.add_argument('--nosmooth', default=False, action='store_true',
					help='Prevent smoothing face detections over a short temporal window')

args = parser.parse_args()
args.img_size = 96

if os.path.isfile(args.face) and args.face.split('.')[1] in ['jpg', 'png', 'jpeg']:
	args.static = True

def get_smoothened_boxes(boxes, T):
	for i in range(len(boxes)):
		if i + T > len(boxes):
			window = boxes[len(boxes) - T:]
		else:
			window = boxes[i : i + T]
		boxes[i] = np.mean(window, axis=0)
	return boxes

def face_detect(images):
	detector = FaceAlignment(LandmarksType._2D, 
											flip_input=False, device=device)

	batch_size = args.face_det_batch_size
	
	while 1:
		predictions = []
		try:
			for i in tqdm(range(0, len(images), batch_size)):
				predictions.extend(detector.get_detections_for_batch(np.array(images[i:i + batch_size])))
		except RuntimeError:
			if batch_size == 1: 
				raise RuntimeError('Image too big to run face detection on GPU. Please use the --resize_factor argument')
			batch_size //= 2
			print('Recovering from OOM error; New batch size: {}'.format(batch_size))
			continue
		break

	results = []
	pady1, pady2, padx1, padx2 = args.pads
	for rect, image in zip(predictions, images):
		if rect is None:
			# 返回 None 表示這一幀沒有人臉，而不是拋出錯誤
			results.append(None)
			continue

		y1 = max(0, rect[1] - pady1)
		y2 = min(image.shape[0], rect[3] + pady2)
		x1 = max(0, rect[0] - padx1)
		x2 = min(image.shape[1], rect[2] + padx2)
		
		results.append([x1, y1, x2, y2])

	# 過濾掉 None 值
	valid_results = [r for r in results if r is not None]
	if len(valid_results) == 0:
		raise ValueError('No faces detected in any frames! Cannot proceed with lip sync.')
	
	# 計算人臉幀比例
	face_ratio = len(valid_results) / len(results)
	print(f"  人臉檢測: {len(valid_results)}/{len(results)} 幀 ({face_ratio*100:.1f}%)")
	
	if face_ratio < 0.5:
		raise ValueError(f'Too few faces detected ({face_ratio*100:.1f}% < 50%)! Cannot ensure quality lip sync.')
	
	boxes = np.array(valid_results)
	if not args.nosmooth: boxes = get_smoothened_boxes(boxes, T=5)
	
	# 為沒有人臉的幀創建佔位符
	valid_idx = 0
	final_results = []
	for i, (image, result) in enumerate(zip(images, results)):
		if result is None:
			final_results.append(None)
		else:
			x1, y1, x2, y2 = boxes[valid_idx]
			final_results.append([image[y1: y2, x1:x2], (y1, y2, x1, x2)])
			valid_idx += 1
	
	results = final_results

	del detector
	return results 

def datagen(frames, mels):
	img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

	if args.box[0] == -1:
		if not args.static:
			face_det_results = face_detect(frames) # BGR2RGB for CNN face detection
		else:
			face_det_results = face_detect([frames[0]])
	else:
		print('Using the specified bounding box instead of face detection...')
	
	# 過濾掉 None 結果（沒有人臉的幀）
	if args.box[0] == -1:
		valid_frames = [(i, f, r) for i, (f, r) in enumerate(zip(frames, face_det_results)) if r is not None]
		if len(valid_frames) == 0:
			raise ValueError('No valid frames with faces detected!')
		frame_indices, frames, face_det_results = zip(*valid_frames)
		frames = list(frames)
		face_det_results = list(face_det_results)
	else:
		# 使用指定的 bounding box
		y1, y2, x1, x2 = args.box
		face_det_results = [[f[y1: y2, x1:x2], (y1, y2, x1, x2)] for f in frames]

	for i, m in enumerate(mels):
		idx = 0 if args.static else i%len(frames)
		frame_to_save = frames[idx].copy()
		
		# 解包 face_det_results，確保數據有效
		face_data = face_det_results[idx]
		if isinstance(face_data, list) and len(face_data) == 2:
			face, coords = face_data[0], face_data[1]
		else:
			raise ValueError(f"Invalid face_det_results format at index {idx}: {type(face_data)}")
		
		# 驗證 face 數據
		if face is None or not isinstance(face, np.ndarray):
			raise ValueError(f"Face data is None or invalid at index {idx}")
		if face.size == 0 or face.shape[0] == 0 or face.shape[1] == 0:
			raise ValueError(f"Face region is empty at index {idx}. Shape: {face.shape}")
		
		# 安全地 resize
		try:
			face = cv2.resize(face, (args.img_size, args.img_size))
		except cv2.error as e:
			print(f"❌ Resize 失敗 at frame {idx}: face shape={face.shape}, error={e}")
			raise
			
		img_batch.append(face)
		mel_batch.append(m)
		frame_batch.append(frame_to_save)
		coords_batch.append(coords)

		if len(img_batch) >= args.wav2lip_batch_size:
			img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

			img_masked = img_batch.copy()
			img_masked[:, args.img_size//2:] = 0

			img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
			mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

			yield img_batch, mel_batch, frame_batch, coords_batch
			img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

	if len(img_batch) > 0:
		img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

		img_masked = img_batch.copy()
		img_masked[:, args.img_size//2:] = 0

		img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
		mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

		yield img_batch, mel_batch, frame_batch, coords_batch

mel_step_size = 16

def get_device_with_fallback():
    """智能選擇設備，自動處理不支援的設備類型"""
    # 優先順序: CUDA > MPS > CPU
    if torch.cuda.is_available():
        return 'cuda'
    
    # 嘗試使用 MPS（Apple Silicon GPU）
    if torch.backends.mps.is_available():
        try:
            # 測試 face_detection 是否支援 MPS
            from face_detection import FaceAlignment, LandmarksType
            test_detector = FaceAlignment(LandmarksType._2D, flip_input=False, device='mps')
            del test_detector
            print("✅ face_detection 模組支援 MPS，使用 MPS 加速")
            return 'mps'
        except (ValueError, RuntimeError) as e:
            print(f"⚠️  MPS 可用但 face_detection 模組不支援 (錯誤: {type(e).__name__})")
            print("   自動降級使用 CPU")
            return 'cpu'
    
    return 'cpu'

device = get_device_with_fallback()
print(f"🖥️  Wav2Lip 推理設備: {device.upper()}")

def _load(checkpoint_path):
	if device == 'cuda':
		checkpoint = torch.load(checkpoint_path)
	else:
		checkpoint = torch.load(checkpoint_path,
								map_location=lambda storage, loc: storage)
	return checkpoint

def load_model(path):
	model = Wav2Lip()
	print("Load checkpoint from: {}".format(path))
	checkpoint = _load(path)
	s = checkpoint["state_dict"]
	new_s = {}
	for k, v in s.items():
		new_s[k.replace('module.', '')] = v
	model.load_state_dict(new_s)

	model = model.to(device)
	return model.eval()

def run_inference(face_path, audio_path, output_path):
	args.face = face_path
	args.audio = audio_path
	args.outfile = output_path
	
	if not os.path.isfile(args.face):
		raise ValueError('--face argument must be a valid path to video/image file')

	elif args.face.split('.')[1] in ['jpg', 'png', 'jpeg']:
		full_frames = [cv2.imread(args.face)]
		fps = args.fps

	else:
		video_stream = cv2.VideoCapture(args.face)
		fps = video_stream.get(cv2.CAP_PROP_FPS)

		print('Reading video frames...')

		full_frames = []
		while 1:
			still_reading, frame = video_stream.read()
			if not still_reading:
				video_stream.release()
				break
			if args.resize_factor > 1:
				frame = cv2.resize(frame, (frame.shape[1]//args.resize_factor, frame.shape[0]//args.resize_factor))

			if args.rotate:
				frame = cv2.rotate(frame, cv2.cv2.ROTATE_90_CLOCKWISE)

			y1, y2, x1, x2 = args.crop
			if x2 == -1: x2 = frame.shape[1]
			if y2 == -1: y2 = frame.shape[0]

			frame = frame[y1:y2, x1:x2]

			full_frames.append(frame)

	print ("Number of frames available for inference: "+str(len(full_frames)))

	if not args.audio.endswith('.wav'):
		print('Extracting raw audio...')
		command = 'ffmpeg -y -i {} -strict -2 {}'.format(args.audio, 'temp/temp.wav')

		subprocess.call(command, shell=True)
		args.audio = 'temp/temp.wav'

	wav = audio.load_wav(args.audio, 16000)
	mel = audio.melspectrogram(wav)
	print(mel.shape)

	if np.isnan(mel.reshape(-1)).sum() > 0:
		raise ValueError('Mel contains nan! Using a TTS voice? Add a small epsilon noise to the wav file and try again')

	mel_chunks = []
	mel_idx_multiplier = 80./fps 
	i = 0
	while 1:
		start_idx = int(i * mel_idx_multiplier)
		if start_idx + mel_step_size > len(mel[0]):
			mel_chunks.append(mel[:, len(mel[0]) - mel_step_size:])
			break
		mel_chunks.append(mel[:, start_idx : start_idx + mel_step_size])
		i += 1

	print("Length of mel chunks: {}".format(len(mel_chunks)))

	full_frames = full_frames[:len(mel_chunks)]

	batch_size = args.wav2lip_batch_size
	gen = datagen(full_frames.copy(), mel_chunks)

	for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(gen, 
												total=int(np.ceil(float(len(mel_chunks))/batch_size)))):
		if i == 0:
			model = load_model(args.checkpoint_path)
			print ("Model loaded")

			frame_h, frame_w = full_frames[0].shape[:-1]
			out = cv2.VideoWriter('temp/result.avi', 
									cv2.VideoWriter_fourcc(*'DIVX'), fps, (frame_w, frame_h))

		img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device)
		mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)

		with torch.no_grad():
			pred = model(mel_batch, img_batch)

		pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.
		
		for p, f, c in zip(pred, frames, coords):
			y1, y2, x1, x2 = c
			p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))

			f[y1:y2, x1:x2] = p
			out.write(f)

	out.release()

	command = 'ffmpeg -y -i {} -i {} -strict -2 -q:v 1 {}'.format(args.audio, 'temp/result.avi', args.outfile)
	subprocess.call(command, shell=platform.system() != 'Windows')
	
	return output_path

# if __name__ == '__main__':
# 	main()
