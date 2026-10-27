"""Fail early if the target machine lacks usable CUDA."""
import torch
import transformers
import llama_cpp

if not torch.cuda.is_available():
    raise SystemExit('CUDA unavailable: install/update the NVIDIA driver and rerun setup.')
print(torch.cuda.get_device_name(0))
print('VRAM GiB:', torch.cuda.get_device_properties(0).total_memory / 2**30)
print('torch:', torch.__version__, 'transformers:', transformers.__version__,
      'llama-cpp-python:', llama_cpp.__version__)
if torch.cuda.get_device_properties(0).total_memory < 10 * 2**30:
    raise SystemExit('Expected the 12 GB GPU. Select the correct CUDA device before running.')
