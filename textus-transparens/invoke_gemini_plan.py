import subprocess
import os

with open("C:/Users/thene/projects/tt/gemini_prompt_template.txt", "r", encoding="utf-8") as f:
    template = f.read()

with open("C:/Users/thene/OneDrive/Desktop/Textus_Transparens_Full_PRD_v1.1.md", "r", encoding="utf-8") as f:
    prd = f.read()

with open("C:/Users/thene/projects/tt/models.py", "r", encoding="utf-8") as f:
    models = f.read()

full_prompt = template.replace("[INSERT_PRD_HERE]", prd).replace("[INSERT_MODELS_HERE]", models)

# Use subprocess to call gemini
process = subprocess.Popen(
    ["gemini.cmd", "-m", "pro", "--approval-mode", "yolo"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    shell=True
)

stdout, stderr = process.communicate(input=full_prompt)

if process.returncode == 0:
    with open("C:/Users/thene/projects/tt/upgrade_plan_v1.1.md", "w", encoding="utf-8") as f:
        f.write(stdout)
    print("Plan generated successfully!")
else:
    print(f"Error generating plan: {stderr}")
