"""
Git wrapper utilities for the OpenGameAssetLibrary
Provides functions to interact with git repository for tracking asset changes
"""

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
        if result.returncode != 0 and result.stderr:
            print(f"Git warning: {result.stderr}")
        return result.stdout.strip(), result.returncode
    except Exception as e:
        print(f"Git error: {e}")
        return str(e), 1

def get_file_history(file_path):
    """Get the git history for a specific file"""
    try:
        log_output, return_code = run_git(f'log --oneline -- {file_path}')
        
        if return_code != 0:
            return []
        
        commits = []
        for line in log_output.split('\n'):
            if line.strip():
                parts = line.split(' ', 1)
                commits.append({
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else "",
                    "short_hash": parts[0][:7]
                })
        
        return commits
    except Exception as e:
        print(f"Error getting file history: {e}")
        return []

def get_repo_status():
    """Get current repository status"""
    try:
        status_output, _ = run_git("status --porcelain")
        branch_output, _ = run_git("rev-parse --abbrev-ref HEAD")
        
        changed_files = []
        if status_output.strip():
            for line in status_output.strip().split('\n'):
                if line.strip():
                    status_code = line[:2]
                    filename = line[3:]
                    changed_files.append({
                        "file": filename,
                        "status": status_code.strip()
                    })
        
        return {
            "branch": branch_output or "main",
            "changed_files": changed_files,
            "changes_count": len(changed_files)
        }
    except Exception as e:
        print(f"Error getting repo status: {e}")
        return {
            "branch": "unknown",
            "changed_files": [],
            "changes_count": 0
        }

def commit_changes(message, files=None):
    """Add and commit changes with a message"""
    try:
        if files:
            for file in files:
                run_git(f"add {file}")
        else:
            run_git("add .")
        
        output, return_code = run_git(f'commit -m "{message}"')
        return return_code == 0, output
    except Exception as e:
        print(f"Error committing changes: {e}")
        return False, str(e)

def init_repo():
    """Initialize git repository if it doesn't exist"""
    if not os.path.exists(os.path.join(LIBRARY_PATH, ".git")):
        try:
            os.makedirs(LIBRARY_PATH, exist_ok=True)
            run_git("init")
            run_git("config user.name 'Asset Library System'")
            run_git("config user.email 'library@example.com'")
            return True
        except Exception as e:
            print(f"Error initializing repo: {e}")
            return False
    return True