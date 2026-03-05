import torch
import onnxruntime as ort

print("--- Hardware Check ---")

# Torch Check
print(f"Torch version: {torch.__version__}")
# Note: On Windows, torch-directml is needed for AMD GPU, but let's check standard CUDA/CPU first
print(f"CUDA available: {torch.cuda.is_available()}")

# ONNX Runtime Check
print(f"ONNX Runtime version: {ort.__version__ if hasattr(ort, '__version__') else 'Unknown'}")
providers = ort.get_available_providers()
print(f"Available ONNX providers: {providers}")

if "DmlExecutionProvider" in providers:
    print("✅ DirectML (AMD GPU) is available for ONNX!")
else:
    print("❌ DirectML (AMD GPU) is NOT found in ONNX providers.")

if "VitisAIExecutionProvider" in providers:
    print("✅ VitisAI (AMD NPU) is available for ONNX!")
else:
    print("❌ VitisAI (AMD NPU) is NOT found in ONNX providers.")
