"""Git wrapper utilities"""
import subprocess
import os

LIBRARY_PATH = "./library-repo"

def run_git(command):
    """Execute git command in the library directory"""
    try:
        result = subprocess.run(
            f"git -C {LIBRARY_PATH} {command}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
            
        return result.stdout.strip(), result.returncode
    except Exception as e:
        raise Exception(f"Git error: {str(e)}")

def get_file_history(filepath):
    """Get the git history for a specific file"""
    try:
        log_output, _ = run_git(f'log --pretty=format:"%H|%an|%ad|%s" --date=iso -- {filepath}')
        
        commits = []
        for line in log_output.split('\n'):
            if line:
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    })
        
        return commits
    except Exception as e:
        return []

def get_current_branch():
    """Get the current git branch name"""
    try:
        branch, _ = run_git("rev-parse --abbrev-ref HEAD")
        return branch
    except:
        return "main"

def init_repo():
    """Initialize git repository if it doesn't exist"""
    if not os.path.exists(os.path.join(LIBRARY_PATH, ".git")):
        os.makedirs(LIBRARY_PATH, exist_ok=True)
        run_git("init")
        run_git("config user.email 'library@example.com'")
        run_git("config user.name 'Asset Library'")
        
        # Create initial assets directory
        assets_dir = os.path.join(LIBRARY_PATH, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Create .gitignore
        gitignore_path = os.path.join(LIBRARY_PATH, ".gitignore")
        with open(gitignore_path, 'w') as f:
            f.write("*.pyc\n__pycache__/\n.DS_Store\n")
        
        run_git("add .")
        run_git('commit -m "Initial library setup"')
        return True
    return False