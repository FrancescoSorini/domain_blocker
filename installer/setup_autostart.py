import os
import subprocess
from pathlib import Path

TASK_NAME = "DNSDomainBlocker"

def create_task():
    python_path = Path(os.sys.executable).resolve()
    script_path = Path(__file__).parent.parent / "main.py"

    cmd = f'schtasks /create /tn "{TASK_NAME}" /tr "{python_path} {script_path}" /sc onlogon /rl highest /f'
    print("Creazione task scheduler:")
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)
    print("Task creato con successo! L'app partirà al login.")

def delete_task():
    cmd = f'schtasks /delete /tn "{TASK_NAME}" /f'
    subprocess.run(cmd, shell=True)
    print("Task rimosso.")

if __name__ == "__main__":
    create_task()
