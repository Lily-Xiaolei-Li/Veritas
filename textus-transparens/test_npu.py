import onnxruntime as ort
import os

model_path = r"C:\Users\thene\.cache\bge-m3-onnx-npu\bge-m3-int8.onnx"

print(f"Available providers: {ort.get_available_providers()}")

# AMD VitisAI (NPU) configuration
config_file = r"C:\Program Files\RyzenAI\1.7.0\voe-4.0-win_amd64\vaip_config.json"

try:
    if os.path.exists(config_file):
        providers = [
            ('VitisAIExecutionProvider', {
                'config_file': config_file,
                'cacheDir': r'C:\Users\thene\.cache\vitis_ai_cache',
                'cacheKey': 'bge_m3_npu'
            }),
            'CPUExecutionProvider'
        ]
        session = ort.InferenceSession(model_path, providers=providers)
        print(f"NPU Session initialized successfully! Providers: {session.get_providers()}")
    else:
        print("Vitis AI config file not found.")
except Exception as e:
    print(f"NPU Session failed: {e}")
