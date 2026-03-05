import onnxruntime as ort
import numpy as np
from transformers import AutoTokenizer
import time
import os

def benchmark_bge(provider_name):
    model_path = r"C:\Users\thene\.cache\bge-m3-onnx-npu\bge-m3-int8.onnx"
    tokenizer_name = "BAAI/bge-m3"
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    text = "This is a benchmark sentence for comparing NPU and CPU performance on the GEEKOM A9 Max."
    inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=512)
    
    input_dict = {
        'input_ids': inputs['input_ids'].astype(np.int64),
        'attention_mask': inputs['attention_mask'].astype(np.int64)
    }

    if provider_name == "NPU":
        config_file = r"C:\Program Files\RyzenAI\1.7.0\voe-4.0-win_amd64\vaip_config.json"
        providers = [
            ('VitisAIExecutionProvider', {
                'config_file': config_file,
                'cacheDir': r'C:\Users\thene\.cache\vitis_ai_cache',
                'cacheKey': 'benchmark_npu'
            }),
            'CPUExecutionProvider'
        ]
    else:
        providers = ['CPUExecutionProvider']

    print(f"\n--- Benchmarking {provider_name} ---")
    
    # 1. Initialization & First Run (Cold start)
    start_init = time.time()
    session = ort.InferenceSession(model_path, providers=providers)
    init_time = time.time() - start_init
    
    start_first = time.time()
    session.run(None, input_dict)
    first_run_time = time.time() - start_first
    
    print(f"Init time: {init_time:.4f}s")
    print(f"First run time (Warm up): {first_run_time:.4f}s")

    # 2. Loop for Average (Steady state)
    iterations = 50
    times = []
    for _ in range(iterations):
        t0 = time.time()
        session.run(None, input_dict)
        times.append(time.time() - t0)
    
    avg_time = sum(times) / iterations
    print(f"Average time over {iterations} runs: {avg_time*1000:.2f}ms")
    return avg_time * 1000

if __name__ == "__main__":
    import sys
    # We will run this script twice, once for CPU and once for NPU using the appropriate python executable
    mode = sys.argv[1] if len(sys.argv) > 1 else "CPU"
    benchmark_bge(mode)
