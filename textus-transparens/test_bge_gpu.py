import onnxruntime as ort
import numpy as np
from transformers import AutoTokenizer
import time

def test_bge_gpu():
    # Test FP32 model this time
    model_path = r"C:\Users\thene\.cache\bge-m3-onnx-npu\bge-m3.onnx"
    tokenizer_name = "BAAI/bge-m3"
    
    print(f"Available providers: {ort.get_available_providers()}")
    
    # Try DirectML explicitly
    try:
        print("\n--- Testing DirectML ---")
        sess_options = ort.SessionOptions()
        session = ort.InferenceSession(model_path, providers=['DmlExecutionProvider', 'CPUExecutionProvider'], sess_options=sess_options)
        print(f"Session using: {session.get_providers()}")
        
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        text = "This is a test to see if GPU acceleration works for BGE-M3 on Radeon 890M."
        inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=512)
        
        start = time.time()
        outputs = session.run(None, {
            'input_ids': inputs['input_ids'].astype(np.int64),
            'attention_mask': inputs['attention_mask'].astype(np.int64)
        })
        print(f"DirectML Success! Time: {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"DirectML Failed: {e}")

    # Try CPU for baseline
    try:
        print("\n--- Testing CPU ---")
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=512)
        
        start = time.time()
        outputs = session.run(None, {
            'input_ids': inputs['input_ids'].astype(np.int64),
            'attention_mask': inputs['attention_mask'].astype(np.int64)
        })
        print(f"CPU Success! Time: {(time.time() - start)*1000:.2f}ms")
    except Exception as e:
        print(f"CPU Failed: {e}")

if __name__ == "__main__":
    test_bge_gpu()
