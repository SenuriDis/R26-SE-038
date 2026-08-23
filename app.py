import os
from datetime import datetime

from flask_cors import CORS

from flask import Flask, request, jsonify

# Import analyzer functions from main.py
from main import (
    analyze_file,
    analyze_folder,
    analyze_file_with_requirements,
    analyze_file_with_auto_requirements,
    analyze_github_repository,
)

# Import helper function to save JSON results
from src.output.json_formatter import save_json_to_file

# Import MongoDB collection
from src.config.db import analysis_collection


# Create Flask application
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Folder used to store uploaded Python files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/", methods=["GET"])
def home():
    # Simple route to check whether API is running
    return jsonify({
        "message": "Static Code Analysis API is running"
    })


@app.route("/analyze-file", methods=["POST"])
def analyze_single_file():
    # Get JSON data from request body
    data = request.get_json()

    # Validate file_path
    if not data or "file_path" not in data:
        return jsonify({
            "error": "file_path is required"
        }), 400

    file_path = data["file_path"]

    # Analyze the given Python file
    result = analyze_file(file_path)

    if result is None:
        return jsonify({
            "error": "Analysis failed. Check file path or source code."
        }), 400

    # Save API result to JSON file
    save_json_to_file(result, "results/analysis_results.json")

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "file_path_analysis",
        "input_path": file_path,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


@app.route("/analyze-with-requirements", methods=["POST"])
def analyze_file_against_requirements():
    # Get JSON data from request body
    data = request.get_json()

    # Validate file_path and requirement_path
    if not data or "file_path" not in data or "requirement_path" not in data:
        return jsonify({
            "error": "Both file_path and requirement_path are required"
        }), 400

    file_path = data["file_path"]
    requirement_path = data["requirement_path"]

    # Run requirement-aware analysis (AST metrics + risk + spec gaps)
    result = analyze_file_with_requirements(file_path, requirement_path)

    if result is None:
        return jsonify({
            "error": "Analysis failed. Check file path or source code."
        }), 400

    # If requirement parsing failed, surface that error directly
    if "error" in result:
        return jsonify(result), 400

    # Save API result to JSON file
    save_json_to_file(result, "results/requirement_analysis_results.json")

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "requirement_aware_analysis",
        "input_path": file_path,
        "requirement_path": requirement_path,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


@app.route("/analyze-with-auto-requirements", methods=["POST"])
def analyze_file_with_docstring_requirements():
    # Get JSON data from request body
    data = request.get_json()

    # Validate file_path -- no requirement_path needed, it's auto-extracted
    if not data or "file_path" not in data:
        return jsonify({
            "error": "file_path is required"
        }), 400

    file_path = data["file_path"]

    # Run requirement-aware analysis using requirements auto-extracted
    # from the code's own docstrings -- ideal for real, third-party
    # repositories with no hand-written requirement document.
    result = analyze_file_with_auto_requirements(file_path)

    if result is None:
        return jsonify({
            "error": "Analysis failed. Check file path or source code."
        }), 400

    # Save API result to JSON file
    save_json_to_file(result, "results/auto_requirement_analysis_results.json")

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "auto_requirement_aware_analysis",
        "input_path": file_path,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


@app.route("/analyze-github-repo", methods=["POST"])
def analyze_github_repo():
    # Get JSON data from request body
    data = request.get_json()

    # Validate repo_url
    if not data or "repo_url" not in data:
        return jsonify({
            "error": "repo_url is required"
        }), 400

    repo_url = data["repo_url"]
    force_reclone = bool(data.get("force_reclone", False))

    # Clone (or reuse existing clone) and run requirement-aware
    # analysis across every Python file in the repo
    result = analyze_github_repository(repo_url, force_reclone=force_reclone)

    if "error" in result:
        return jsonify(result), 400

    # Save API result to JSON file
    save_json_to_file(result, "results/github_repo_analysis_results.json")

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "github_repo_analysis",
        "repo_url": repo_url,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


@app.route("/analyze-folder", methods=["POST"])
def analyze_project_folder():
    # Get JSON data from request body
    data = request.get_json()

    # Validate folder_path
    if not data or "folder_path" not in data:
        return jsonify({
            "error": "folder_path is required"
        }), 400

    folder_path = data["folder_path"]

    # Analyze all Python files inside the given folder
    results = analyze_folder(folder_path)

    # Save API result to JSON file
    save_json_to_file(results, "results/analysis_results.json")

    # Save results to MongoDB
    analysis_collection.insert_one({
        "type": "folder_analysis",
        "input_path": folder_path,
        "results": results,
        "created_at": datetime.utcnow()
    })

    return jsonify(results), 200


@app.route("/upload-and-analyze", methods=["POST"])
def upload_and_analyze():
    # Check whether a file was uploaded
    if "file" not in request.files:
        return jsonify({
            "error": "No file uploaded"
        }), 400

    file = request.files["file"]

    # Check whether filename is empty
    if file.filename == "":
        return jsonify({
            "error": "Empty filename"
        }), 400

    # Allow only Python files
    if not file.filename.endswith(".py"):
        return jsonify({
            "error": "Only .py files allowed"
        }), 400

    # Save uploaded file into uploads folder
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # Analyze uploaded Python file
    result = analyze_file(file_path)

    if result is None:
        return jsonify({
            "error": "Analysis failed"
        }), 400

    # Save API result to JSON file
    save_json_to_file(result, "results/analysis_results.json")

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "file_upload_analysis",
        "file_name": file.filename,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


@app.route("/analysis-results", methods=["GET"])
def get_analysis_results():
    # Fetch all saved reports from MongoDB
    reports = []

    for report in analysis_collection.find().sort("created_at", -1):
        report["_id"] = str(report["_id"])
        reports.append(report)

    return jsonify(reports), 200


if __name__ == "__main__":
    # Run Flask development server
    app.run(debug=False, use_reloader=False)