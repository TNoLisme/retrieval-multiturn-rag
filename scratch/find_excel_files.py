import os
import sys

if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print(f"Scanning for Excel files in: {project_root}")
    found = False
    for root, dirs, files in os.walk(project_root):
        # Skip some temp directories
        if ".git" in root or "__pycache__" in root or "vas_vector_db" in root:
            continue
        for file in files:
            if file.endswith(".xlsx"):
                print(f"  - {os.path.join(root, file)}")
                found = True
    if not found:
        print("No Excel files found except the default ones.")

if __name__ == "__main__":
    main()
