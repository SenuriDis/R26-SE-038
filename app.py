import os
from datetime import datetime

from flask_cors import CORS

from flask import Flask, request, jsonify

# Import analyzer functions from main.py
from main import analyze_file, analyze_folder

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