import os

OUTPUT_FILE = "project_context.md"
EXTENSIONS = {'.py', '.yml', '.yaml', '.md', '.conf', '.env.example'}
EXCLUDE_DIRS = {'.git', '.vscode', '__pycache__', 'venv', 'logs', 'node_modules', '.pytest_cache', 'scratch'}

def collect_project_info():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write("# Project Context\n\n")
        outfile.write("This document contains all source code and configuration files for the Crawler and AIOps Controller project.\n\n")
        
        for root, dirs, files in os.walk('.'):
            # modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if file == 'Dockerfile' or ext in EXTENSIONS:
                    filepath = os.path.join(root, file)
                    
                    # Skip the generator script and the output file itself
                    if file == OUTPUT_FILE or file == 'generate_context.py' or file == 'requirements.txt':
                        continue
                        
                    try:
                        with open(filepath, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                        # Use appropriate markdown language tag
                        lang = ext.replace('.', '')
                        if file == 'Dockerfile':
                            lang = 'dockerfile'
                        
                        # Normalize path for better reading
                        display_path = filepath.replace('.\\', '').replace('\\', '/')
                        
                        outfile.write(f"## File: {display_path}\n\n")
                        outfile.write(f"```{lang}\n")
                        outfile.write(content)
                        outfile.write(f"\n```\n\n")
                    except Exception as e:
                        print(f"Skipping {filepath} due to error: {e}")

if __name__ == "__main__":
    collect_project_info()
    print(f"Successfully generated {OUTPUT_FILE}")
