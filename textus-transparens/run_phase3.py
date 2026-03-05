import subprocess
import os

def run_prompt(prompt_path, output_path, model="pro"):
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    with open("C:/Users/thene/projects/tt/models.py", "r", encoding="utf-8") as f:
        models = f.read()

    with open("C:/Users/thene/projects/tt/ai_manager.py", "r", encoding="utf-8") as f:
        ai_manager = f.read()

    full_prompt = template.replace("[INSERT_MODELS_HERE]", models).replace("[INSERT_AI_MANAGER_HERE]", ai_manager)
    full_prompt += "\n\nCRITICAL: Return ONLY raw Python code. DO NOT include any markdown code blocks (no ```python), NO explanation, and NO conversational filler. Your entire response must be valid Python code."

    process = subprocess.Popen(
        ["gemini.cmd", "-m", model, "--approval-mode", "yolo"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        shell=True
    )

    stdout, stderr = process.communicate(input=full_prompt)

    if process.returncode == 0:
        output = stdout.strip()
        if "```python" in output:
            output = output.split("```python")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Generated {output_path}")
    else:
        print(f"Error for {prompt_path}: {stderr}")

# Phase 3 Task 1 Prompt
task_prompt = """You are the Lead Developer for 'Textus Transparens' (TT).
Task: Create 'C:\\Users\\thene\\projects\\tt\\ai_sense_manager.py'.

Requirements:
1. perform_ai_sense(project_dir, framework_id, source_id=None, provider='gemini', model='pro')
   - Fetch the theoretical framework and its dimensions.
   - Fetch all extracts (for the project or specific source).
   - Construct a prompt asking the AI to find 'tensions' or 'overlaps' between framework dimensions within each extract.
   - Use 'extract_json_array' from 'ai_manager.py' to parse the output.
   - Save results to the 'code_intersections' table with 'is_ai_generated=True'.
2. Use SQLAlchemy for all DB operations.

Context Models:
[INSERT_MODELS_HERE]

Context AI Manager:
[INSERT_AI_MANAGER_HERE]
"""

with open("C:/Users/thene/projects/tt/phase3_task1_prompt.txt", "w", encoding="utf-8") as f:
    f.write(task_prompt)

run_prompt("C:/Users/thene/projects/tt/phase3_task1_prompt.txt", "C:/Users/thene/projects/tt/ai_sense_manager.py")
