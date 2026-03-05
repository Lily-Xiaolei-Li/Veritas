import subprocess
import os

def run_prompt(prompt_path, output_path, model="pro"):
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    with open("C:/Users/thene/projects/tt/models.py", "r", encoding="utf-8") as f:
        models = f.read()

    with open("C:/Users/thene/projects/tt/code_manager.py", "r", encoding="utf-8") as f:
        code_manager = f.read()

    full_prompt = template.replace("[INSERT_MODELS_HERE]", models).replace("[INSERT_CODE_MANAGER_HERE]", code_manager)
    full_prompt += "\n\nCRITICAL: Return ONLY the Python code. Do not include any explanation or conversational filler."

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
        # Simple cleanup if gemini wraps in markdown
        output = stdout.strip()
        if output.startswith("```python"):
            output = output.split("```python")[1].split("```")[0].strip()
        elif output.startswith("```"):
            output = output.split("```")[1].split("```")[0].strip()
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Generated {output_path}")
    else:
        print(f"Error for {prompt_path}: {stderr}")

# Run Phase 2 tasks
run_prompt("C:/Users/thene/projects/tt/phase2_task1_prompt.txt", "C:/Users/thene/projects/tt/advanced_matrix_manager.py")
run_prompt("C:/Users/thene/projects/tt/phase2_task2_prompt.txt", "C:/Users/thene/projects/tt/gpviz_export_manager.py")
