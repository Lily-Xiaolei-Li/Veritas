"""
本地模型基准测试 - 小蕾出品 🌸
测试任务：让模型写一个简单的 Python 函数
"""
import requests
import time
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

# 测试任务：写一个计算斐波那契数列的函数
CODING_TASK = """Write a Python function called `fibonacci(n)` that:
1. Takes an integer n as input
2. Returns the nth Fibonacci number (0-indexed, so fibonacci(0)=0, fibonacci(1)=1, fibonacci(10)=55)
3. Include proper error handling for negative inputs
4. Add a docstring explaining the function

Return ONLY the Python code, no explanation needed."""

MODELS = [
    "deepseek-r1:14b",
    "qwen2.5:14b", 
    "llama3.1:8b"
]

def test_model(model_name: str) -> dict:
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"🧪 测试模型: {model_name}")
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
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        result = response.json()
        output = result.get("response", "")
        
        # 统计信息
        eval_count = result.get("eval_count", 0)
        eval_duration = result.get("eval_duration", 0) / 1e9  # 转换为秒
        tokens_per_sec = eval_count / eval_duration if eval_duration > 0 else 0
        
        print(f"✅ 完成! 用时: {elapsed:.2f}秒")
        print(f"📊 生成 tokens: {eval_count}")
        print(f"⚡ 速度: {tokens_per_sec:.2f} tokens/秒")
        print(f"\n📝 输出内容:")
        print("-" * 40)
        print(output[:1500] if len(output) > 1500 else output)
        print("-" * 40)
        
        return {
            "model": model_name,
            "success": True,
            "elapsed_seconds": round(elapsed, 2),
            "eval_count": eval_count,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "output_length": len(output),
            "output_preview": output[:500]
        }
        
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"❌ 失败! 错误: {e}")
        return {
            "model": model_name,
            "success": False,
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e)
        }

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("🌸 小蕾的本地模型基准测试 🌸")
    print(f"测试任务: 编写斐波那契函数")
    print(f"测试模型: {', '.join(MODELS)}")
    print("=" * 60)
    
    results = []
    for model in MODELS:
        result = test_model(model)
        results.append(result)
        print("\n⏳ 休息5秒让GPU冷却...")
        time.sleep(5)
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"{'模型':<20} {'用时(秒)':<12} {'Tokens':<10} {'速度(t/s)':<12} {'状态'}")
    print("-" * 60)
    
    for r in results:
        if r["success"]:
            print(f"{r['model']:<20} {r['elapsed_seconds']:<12} {r.get('eval_count', 'N/A'):<10} {r.get('tokens_per_sec', 'N/A'):<12} ✅")
        else:
            print(f"{r['model']:<20} {r['elapsed_seconds']:<12} {'N/A':<10} {'N/A':<12} ❌")
    
    # 找出最快和最慢
    successful = [r for r in results if r["success"]]
    if successful:
        fastest = min(successful, key=lambda x: x["elapsed_seconds"])
        most_tokens = max(successful, key=lambda x: x.get("tokens_per_sec", 0))
        print(f"\n🏆 最快完成: {fastest['model']} ({fastest['elapsed_seconds']}秒)")
        print(f"⚡ 最高吞吐: {most_tokens['model']} ({most_tokens.get('tokens_per_sec', 0)} tokens/秒)")
    
    # 保存结果
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n💾 结果已保存到 benchmark_results.json")

if __name__ == "__main__":
    main()
