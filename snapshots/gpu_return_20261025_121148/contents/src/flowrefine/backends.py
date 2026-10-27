"""Optional CPU model adapters. No credentials or paid network services required."""

import gc
import base64
import hashlib
import importlib.metadata
import time
from pathlib import Path


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


class LlamaCPU:
    def __init__(self, model_path, threads=4, context=4096, seed=241024):
        self.model_path = str(Path(model_path).resolve())
        self.threads, self.context, self.seed = threads, context, seed
        self.model = None

    def _load(self):
        if self.model is None:
            from llama_cpp import Llama
            self.model = Llama(model_path=self.model_path, n_ctx=self.context,
                               n_threads=self.threads, n_gpu_layers=0,
                               seed=self.seed, verbose=False)

    def complete(self, messages, max_tokens=900, json_output=True):
        started = time.perf_counter()
        self._load()
        if json_output:
            from .prompts import COMPACT_SCHEMA
            options = {"response_format": {"type": "json_object", "schema": COMPACT_SCHEMA}}
        else:
            options = {}
        response = self.model.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=0.0,
            top_p=1.0, seed=self.seed, **options)
        text = response["choices"][0]["message"]["content"] or ""
        return {"text": text, "elapsed_seconds": time.perf_counter()-started,
                "usage": response.get("usage", {}),
                "finish_reason": response["choices"][0].get("finish_reason"),
                "backend": "llama-cpp-python", "runtime_version": package_version("llama-cpp-python"),
                "model": self.model_path, "device": "cpu", "seed": self.seed,
                "temperature": 0.0}

    def close(self):
        if self.model is not None:
            self.model.close()
            self.model = None
        gc.collect()


class HFVisionCPU:
    """Compact Transformers VLM, loaded in a separate experimental phase."""

    def __init__(self, model_path, threads=4):
        self.model_path, self.threads = str(model_path), threads
        self.model = self.processor = None

    def _load(self):
        if self.model is None:
            import torch
            from transformers import AutoProcessor, AutoModelForVision2Seq
            torch.set_num_threads(self.threads)
            self.processor = AutoProcessor.from_pretrained(self.model_path, local_files_only=True)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_path, torch_dtype=torch.float32, local_files_only=True,
                attn_implementation="eager").eval().to("cpu")

    def critique(self, messages, image_path, max_tokens=180):
        from PIL import Image
        import torch
        started = time.perf_counter()
        self._load()
        image_path = Path(image_path)
        with Image.open(image_path) as original:
            picture = original.convert("RGB")
        # Same raster resolution policy for all tasks; no reference access.
        picture.thumbnail((800, 1200))
        multimodal = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": "\n".join(m["content"] for m in messages)}]}]
        prompt = self.processor.apply_chat_template(multimodal, add_generation_prompt=True)
        inputs = self.processor(text=prompt, images=[picture], return_tensors="pt")
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                                         use_cache=True)
        prefix = inputs["input_ids"].shape[1]
        text = self.processor.batch_decode(output[:, prefix:], skip_special_tokens=True)[0]
        return {"text": text, "elapsed_seconds": time.perf_counter()-started,
                "usage": {"prompt_tokens": prefix, "completion_tokens": output.shape[1]-prefix},
                "backend": "transformers", "runtime_version": package_version("transformers"),
                "model": self.model_path, "device": "cpu", "temperature": 0.0,
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()}

    def close(self):
        self.model = self.processor = None
        gc.collect()


class MTMDVisionCPU:
    """GGUF vision-language model plus projector, CPU only, no PyTorch."""

    def __init__(self, model_path, projector_path, threads=4, context=4096):
        self.model_path = str(Path(model_path).resolve())
        self.projector_path = str(Path(projector_path).resolve())
        self.threads, self.context = threads, context
        self.model = self.handler = None

    def _load(self):
        if self.model is None:
            from llama_cpp import Llama
            from llama_cpp.llama_chat_format import MTMDChatHandler
            self.handler = MTMDChatHandler(clip_model_path=self.projector_path,
                                           verbose=False, use_gpu=False)
            self.model = Llama(model_path=self.model_path, chat_handler=self.handler,
                               n_ctx=self.context, n_threads=self.threads,
                               n_gpu_layers=0, seed=241024, verbose=False)

    def critique(self, messages, image_path, max_tokens=180):
        started = time.perf_counter()
        self._load()
        image_path = Path(image_path)
        picture = image_path.read_bytes()
        encoded = base64.b64encode(picture).decode("ascii")
        content = [{"type": "text", "text": "\n".join(m["content"] for m in messages)},
                   {"type": "image_url", "image_url": {"url": "data:image/png;base64,"+encoded}}]
        response = self.model.create_chat_completion(
            messages=[{"role": "user", "content": content}],
            max_tokens=max_tokens, temperature=0.0, top_p=1.0, seed=241024)
        return {"text": response["choices"][0]["message"]["content"] or "",
                "elapsed_seconds": time.perf_counter()-started,
                "usage": response.get("usage", {}),
                "finish_reason": response["choices"][0].get("finish_reason"),
                "backend": "llama-cpp-python-mtmd", "runtime_version": package_version("llama-cpp-python"),
                "model": self.model_path, "projector": self.projector_path,
                "device": "cpu", "temperature": 0.0, "seed": 241024,
                "image_sha256": hashlib.sha256(picture).hexdigest()}

    def close(self):
        if self.model is not None:
            self.model.close()
            self.model = None
        self.handler = None
        gc.collect()
