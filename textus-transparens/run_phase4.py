import subprocess
import os

def run_prompt(prompt_path, output_path, model="pro"):
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    with open("C:/Users/thene/projects/tt/models.py", "r", encoding="utf-8") as f:
        models = f.read()

    full_prompt = template.replace("[INSERT_MODELS_HERE]", models)
    full_prompt += "\n\nCRITICAL: Return ONLY raw Python code. DO NOT include any markdown code blocks, NO explanation, and NO conversational filler. Your entire response must be valid Python code."

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
        # Strip any accidental markdown
        if "```python" in output:
            output = output.split("```python")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Generated {output_path}")
    else:
        print(f"Error for {prompt_path}: {stderr}")

if __name__ == "__main__":
    run_prompt("C:/Users/thene/projects/tt/phase4_task1_prompt.txt", "C:/Users/thene/projects/tt/narrative_manager.py")
