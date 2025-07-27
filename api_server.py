from flask import Flask, jsonify, request
import subprocess
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

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
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def init_library():
    """Initialize the git repository if it doesn't exist"""
    if not os.path.exists(LIBRARY_PATH):
        os.makedirs(LIBRARY_PATH)
        run_git("init")
        
        # Create books directory
        books_dir = os.path.join(LIBRARY_PATH, "books")
        os.makedirs(books_dir, exist_ok=True)
        
        # Add a sample book
        sample_book = {
            "id": str(uuid.uuid4()),
            "title": "The Git Grimoire",
            "author": "System",
            "available": True,
            "current_borrower": None,
            "checkout_history": []
        }
        
        book_path = os.path.join(books_dir, f"{sample_book['id']}.json")
        with open(book_path, 'w') as f:
            json.dump(sample_book, f, indent=2)
        
        run_git("add .")
        run_git('commit -m "Initial library setup"')

@app.route('/browse', methods=['GET'])
def browse():
    """List all books in the library"""
    books = []
    books_dir = os.path.join(LIBRARY_PATH, "books")
    
    if os.path.exists(books_dir):
        for filename in os.listdir(books_dir):
            if filename.endswith('.json'):
                with open(os.path.join(books_dir, filename), 'r') as f:
                    book = json.load(f)
                    books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author": book["author"],
                        "available": book["available"],
                        "current_borrower": book.get("current_borrower")
                    })
    
    return jsonify({"books": books})

@app.route('/checkout', methods=['POST'])
def checkout():
    """Check out a book from the library"""
    data = request.json
    book_id = data.get('book_id')
    borrower = data.get('borrower')
    
    if not book_id or not borrower:
        return jsonify({"error": "Missing book_id or borrower"}), 400
    
    # Find the book
    book_path = os.path.join(LIBRARY_PATH, "books", f"{book_id}.json")
    if not os.path.exists(book_path):
        return jsonify({"error": "Book not found"}), 404
    
    # Load book data
    with open(book_path, 'r') as f:
        book = json.load(f)
    
    if not book["available"]:
        return jsonify({"error": "Book is already checked out"}), 400
    
    # Update book status
    book["available"] = False
    book["current_borrower"] = borrower
    book["checkout_history"].append({
        "borrower": borrower,
        "checked_out": datetime.utcnow().isoformat(),
        "returned": None
    })
    
    # Save updated book
    with open(book_path, 'w') as f:
        json.dump(book, f, indent=2)
    
    # Commit the change
    run_git(f"add {book_path}")
    run_git(f'commit -m "Checkout: {book['title']} to {borrower}"')
    
    return jsonify({
        "message": "Book checked out successfully",
        "book": {
            "id": book["id"],
            "title": book["title"],
            "due_date": "2 weeks from now"  # You can implement actual due dates
        }
    })

@app.route('/return', methods=['POST'])
def return_book():
    """Return a checked out book"""
    data = request.json
    book_id = data.get('book_id')
    borrower = data.get('borrower')
    
    if not book_id or not borrower:
        return jsonify({"error": "Missing book_id or borrower"}), 400
    
    # Find the book
    book_path = os.path.join(LIBRARY_PATH, "books", f"{book_id}.json")
    if not os.path.exists(book_path):
        return jsonify({"error": "Book not found"}), 404
    
    # Load book data
    with open(book_path, 'r') as f:
        book = json.load(f)
    
    if book["available"]:
        return jsonify({"error": "Book is not checked out"}), 400
    
    if book["current_borrower"] != borrower:
        return jsonify({"error": "Book is checked out to someone else"}), 403
    
    # Update book status
    book["available"] = True
    book["current_borrower"] = None
    
    # Update checkout history
    for checkout in reversed(book["checkout_history"]):
        if checkout["borrower"] == borrower and checkout["returned"] is None:
            checkout["returned"] = datetime.utcnow().isoformat()
            break
    
    # Save updated book
    with open(book_path, 'w') as f:
        json.dump(book, f, indent=2)
    
    # Commit the change
    run_git(f"add {book_path}")
    run_git(f'commit -m "Return: {book['title']} from {borrower}"')
    
    return jsonify({"message": "Book returned successfully"})

@app.route('/history/<book_id>', methods=['GET'])
def book_history(book_id):
    """Get the git history for a specific book"""
    book_path = f"books/{book_id}.json"
    log_output, _ = run_git(f'log --oneline -- {book_path}')
    
    commits = []
    for line in log_output.split('\n'):
        if line:
            parts = line.split(' ', 1)
            commits.append({
                "hash": parts[0],
                "message": parts[1] if len(parts) > 1 else ""
            })
    
    return jsonify({"book_id": book_id, "history": commits})

@app.route('/add_book', methods=['POST'])
def add_book():
    """Add a new book to the library"""
    data = request.json
    
    new_book = {
        "id": str(uuid.uuid4()),
        "title": data.get("title", "Untitled"),
        "author": data.get("author", "Unknown"),
        "available": True,
        "current_borrower": None,
        "checkout_history": []
    }
    
    book_path = os.path.join(LIBRARY_PATH, "books", f"{new_book['id']}.json")
    with open(book_path, 'w') as f:
        json.dump(new_book, f, indent=2)
    
    run_git(f"add {book_path}")
    run_git(f'commit -m "Added book: {new_book['title']}"')
    
    return jsonify({"message": "Book added", "book": new_book})

if __name__ == '__main__':
    init_library()
    app.run(debug=True)