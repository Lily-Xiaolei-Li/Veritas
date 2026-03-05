import requests
import json
import re

model_name = "deepseek-r1:14b"
with open("projects/production_test/sources/S0001/canonical/source.md", "r", encoding="utf-8") as f:
    source_text = f.read()

prompt = f"Analyze the following text and find spans that match the code 'Auditability'.\nCode Definition: Tracing analytic decisions\nInclusion Rules: None\n\nReturn ONLY a JSON array of objects with keys 'span' (the exact text snippet) and 'rationale' (why it matches). Do not include any markdown formatting, backticks, or explanation. Text:\n{source_text[:2000]}"

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
)
text_response = response.json().get("response", "")
print("RAW RESPONSE:")
print(text_response)

# Clean Ollama response (remove <think>...</think> blocks)
text_response = re.sub(r'<think>.*?</think>', '', text_response, flags=re.DOTALL).strip()
print("\nCLEANED RESPONSE:")
print(text_response)

json_match = re.search(r'\[\s*\{.*\}\s*\]', text_response, re.DOTALL)
if json_match:
    print("\nMATCHED JSON:")
    print(json_match.group(0))
else:
    print("\nNO JSON MATCH FOUND")
