# -*- coding: utf-8 -*-
"""
本地模型基准测试 - 小蕾出品
测试任务：让模型写一个简单的 Python 函数
"""
import requests
import time
import json
import sys

# 修复 Windows 控制台编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OLLAMA_URL = "http://localhost:11434/api/generate"

# 测试任务：写一个计算斐波那契数列的函数
CODING_TASK = """Write a Python function called `fibonacci(n)` that:
1. Takes an integer n as input
2. Returns the nth Fibonacci number (0-indexed, so fibonacci(0)=0, fibonacci(1)=1, fibonacci(10)=55)
3. Include proper error handling for negative inputs
4. Add a docstring explaining the function

Return ONLY the Python code, no explanation needed."""

MODELS = [
    "llama3.1:8b",      # 最小的，应该最快
    "qwen2.5:14b",      # 中等
    "deepseek-r1:14b",  # 有推理能力，可能最慢但质量最高
]

def test_model(model_name):
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": CODING_TASK,
                "stream": False
            },
            timeout=300
        )
        response.raise_for_status()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        result = response.json()
        output = result.get("response", "")
        
        # 统计信息
        eval_count = result.get("eval_count", 0)
        eval_duration = result.get("eval_duration", 0) / 1e9
        tokens_per_sec = eval_count / eval_duration if eval_duration > 0 else 0
        
        print(f"Done! Time: {elapsed:.2f}s")
        print(f"Tokens: {eval_count}, Speed: {tokens_per_sec:.2f} t/s")
        print(f"Output length: {len(output)} chars")
        print("-" * 40)
        # 只打印前800字符避免太长
        preview = output[:800] if len(output) > 800 else output
        print(preview)
        print("-" * 40)
        
        return {
            "model": model_name,
            "success": True,
            "elapsed_seconds": round(elapsed, 2),
            "eval_count": eval_count,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "output_length": len(output),
            "output": output
        }
        
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"Failed! Error: {e}")
        return {
            "model": model_name,
            "success": False,
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e)
        }

def main():
    print("=" * 60)
    print("Local Model Benchmark Test")
    print("Task: Write a Fibonacci function")
    print(f"Models: {', '.join(MODELS)}")
    print("=" * 60)
    
    results = []
    for model in MODELS:
        result = test_model(model)
        results.append(result)
        print("\nCooling down for 3 seconds...")
        time.sleep(3)
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Model':<20} {'Time(s)':<10} {'Tokens':<10} {'Speed(t/s)':<12} {'Status'}")
    print("-" * 60)
    
    for r in results:
        if r["success"]:
            print(f"{r['model']:<20} {r['elapsed_seconds']:<10} {r.get('eval_count', 'N/A'):<10} {r.get('tokens_per_sec', 'N/A'):<12} OK")
        else:
            print(f"{r['model']:<20} {r['elapsed_seconds']:<10} {'N/A':<10} {'N/A':<12} FAIL")
    
    # 找出最快和最慢
    successful = [r for r in results if r["success"]]
    if successful:
        fastest = min(successful, key=lambda x: x["elapsed_seconds"])
        most_tokens = max(successful, key=lambda x: x.get("tokens_per_sec", 0))
        print(f"\nFastest: {fastest['model']} ({fastest['elapsed_seconds']}s)")
        print(f"Highest throughput: {most_tokens['model']} ({most_tokens.get('tokens_per_sec', 0)} t/s)")
    
    # 保存结果
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nResults saved to benchmark_results.json")

if __name__ == "__main__":
    main()
