"""Lazy, local-only Qwen2.5-VL CUDA adapter for the isolated GPU experiment."""
import gc
import hashlib
import time
from pathlib import Path

from .backends import package_version

MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1024 * 28 * 28
SEED = 241024


class QwenVisionGPU:
    def __init__(self, model_path, revision, seed=SEED):
        self.model_path = str(Path(model_path).resolve())
        self.revision, self.seed = revision, seed
        self.model = self.processor = None

    def _load(self):
        if self.model is None:
            import torch
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            if not torch.cuda.is_available():
                raise RuntimeError('CUDA is unavailable. Install the pinned CUDA runtime and NVIDIA driver.')
            torch.manual_seed(self.seed)
            torch.cuda.manual_seed_all(self.seed)
            self.processor = AutoProcessor.from_pretrained(
                self.model_path, local_files_only=True,
                min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_path, local_files_only=True, torch_dtype=torch.float16,
                device_map={'': 0}, attn_implementation='sdpa').eval()

    def critique(self, messages, image_path, max_tokens=180):
        import torch
        from PIL import Image
        started = time.perf_counter()
        self._load()
        torch.cuda.reset_peak_memory_stats(0)
        with Image.open(image_path) as original:
            picture = original.convert('RGB')
        conversation = [{'role': 'user', 'content': [
            {'type': 'image'},
            {'type': 'text', 'text': '\n'.join(m['content'] for m in messages)}]}]
        prompt = self.processor.apply_chat_template(
            conversation, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[prompt], images=[picture], padding=True,
                                return_tensors='pt').to('cuda:0')
        prefix = inputs['input_ids'].shape[1]
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=max_tokens,
                                         do_sample=False, use_cache=True)
        completion = output[:, prefix:]
        text = self.processor.batch_decode(completion, skip_special_tokens=True,
                                           clean_up_tokenization_spaces=False)[0]
        torch.cuda.synchronize(0)
        count = completion.shape[1]
        return {'text': text, 'elapsed_seconds': time.perf_counter()-started,
                'usage': {'prompt_tokens': prefix, 'completion_tokens': count},
                'finish_reason': 'length' if count >= max_tokens else 'stop',
                'backend': 'transformers-qwen2.5-vl', 'runtime_version': package_version('transformers'),
                'torch_version': torch.__version__, 'model': self.model_path,
                'model_revision': self.revision, 'device': 'cuda:0',
                'gpu_name': torch.cuda.get_device_name(0), 'dtype': 'float16',
                'attn_implementation': 'sdpa', 'seed': self.seed, 'temperature': 0.0,
                'min_pixels': MIN_PIXELS, 'max_pixels': MAX_PIXELS, 'batch_size': 1,
                'peak_gpu_allocated_bytes': torch.cuda.max_memory_allocated(0),
                'peak_gpu_reserved_bytes': torch.cuda.max_memory_reserved(0),
                'image_sha256': hashlib.sha256(Path(image_path).read_bytes()).hexdigest()}

    def close(self):
        self.model = self.processor = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
