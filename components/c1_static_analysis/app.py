import os
import logging
from datetime import datetime

from flask_cors import CORS
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from bson import ObjectId

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
CORS(app)

# Folder used to store uploaded Python files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Keep detailed errors in the server terminal, not in API responses.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_json_object():
    """Return a JSON object from the request, or None if it is invalid."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _required_string(data, *field_names):
    """Validate required string fields without changing API result schemas."""
    if data is None:
        return None, "A valid JSON object is required"

    for field_name in field_names:
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return None, f"{field_name} is required and must be a non-empty string"

    return data, None


def _save_and_store(result, output_path, record):
    """Persist an analysis result to JSON and MongoDB."""
    save_json_to_file(result, output_path)
    analysis_collection.insert_one(record)


# Simple route to check whether API is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Static Code Analysis API is running"
    }), 200


@app.route("/analyze-file", methods=["POST"])
def analyze_single_file():
    data, error = _required_string(_get_json_object(), "file_path")
    if error:
        return jsonify({"error": error}), 400

    file_path = data["file_path"].strip()

    try:
        result = analyze_file(file_path)
        if result is None:
            return jsonify({
                "error": "Analysis failed. Check file path or source code."
            }), 400

        _save_and_store(result, "results/analysis_results.json", {
            "type": "file_path_analysis",
            "input_path": file_path,
            "result": result,
            "created_at": datetime.utcnow()
        })
        return jsonify(result), 200

    except Exception as error:
        logger.exception("Single-file analysis failed")
        return jsonify({"error": "Analysis could not be completed."}), 500


@app.route("/analyze-with-requirements", methods=["POST"])
def analyze_file_against_requirements():
    data, error = _required_string(
        _get_json_object(), "file_path", "requirement_path"
    )
    if error:
        return jsonify({"error": error}), 400

    file_path = data["file_path"].strip()
    requirement_path = data["requirement_path"].strip()

    try:
        result = analyze_file_with_requirements(file_path, requirement_path)
        if result is None:
            return jsonify({
                "error": "Analysis failed. Check file path or source code."
            }), 400

        # Surface requirement parsing errors directly
        if isinstance(result, dict) and "error" in result:
            return jsonify(result), 400

        _save_and_store(result, "results/requirement_analysis_results.json", {
            "type": "requirement_aware_analysis",
            "input_path": file_path,
            "requirement_path": requirement_path,
            "result": result,
            "created_at": datetime.utcnow()
        })
        return jsonify(result), 200

    except Exception as error:
        logger.exception("Requirement-aware analysis failed")
        return jsonify({"error": "Requirement-aware analysis could not be completed."}), 500


@app.route("/analyze-with-auto-requirements", methods=["POST"])
def analyze_file_with_docstring_requirements():
    data, error = _required_string(_get_json_object(), "file_path")
    if error:
        return jsonify({"error": error}), 400

    file_path = data["file_path"].strip()

    try:
        result = analyze_file_with_auto_requirements(file_path)
        if result is None:
            return jsonify({
                "error": "Analysis failed. Check file path or source code."
            }), 400

        if isinstance(result, dict) and "error" in result:
            return jsonify(result), 400

        _save_and_store(result, "results/auto_requirement_analysis_results.json", {
            "type": "auto_requirement_aware_analysis",
            "input_path": file_path,
            "result": result,
            "created_at": datetime.utcnow()
        })
        return jsonify(result), 200

    except Exception as error:
        logger.exception("Automatic requirement analysis failed")
        return jsonify({"error": "Automatic requirement analysis could not be completed."}), 500


@app.route("/analyze-github-repo", methods=["POST"])
def analyze_github_repo():
    data, error = _required_string(_get_json_object(), "repo_url")
    if error:
        return jsonify({"error": error}), 400

    repo_url = data["repo_url"].strip()
    force_reclone = data.get("force_reclone", False)
    if not isinstance(force_reclone, bool):
        return jsonify({"error": "force_reclone must be a boolean"}), 400

    try:
        result = analyze_github_repository(repo_url, force_reclone=force_reclone)
        if not isinstance(result, dict):
            logger.error("GitHub analyzer returned an unexpected result type")
            return jsonify({"error": "Repository analysis returned an invalid result."}), 500
        if "error" in result:
            return jsonify(result), 400

        _save_and_store(result, "results/github_repo_analysis_results.json", {
            "type": "github_repo_analysis",
            "repo_url": repo_url,
            "result": result,
            "created_at": datetime.utcnow()
        })
        return jsonify(result), 200

    except Exception as error:
        logger.exception("GitHub repository analysis failed")
        return jsonify({"error": "GitHub repository analysis could not be completed."}), 500


@app.route("/analyze-folder", methods=["POST"])
def analyze_project_folder():
    data, error = _required_string(_get_json_object(), "folder_path")
    if error:
        return jsonify({"error": error}), 400

    folder_path = data["folder_path"].strip()

    try:
        results = analyze_folder(folder_path)
        if not os.path.isdir(folder_path):
            return jsonify({"error": "Folder not found or invalid."}), 400

        _save_and_store(results, "results/analysis_results.json", {
            "type": "folder_analysis",
            "input_path": folder_path,
            "results": results,
            "created_at": datetime.utcnow()
        })
        return jsonify(results), 200

    except Exception as error:
        logger.exception("Folder analysis failed")
        return jsonify({"error": "Folder analysis could not be completed."}), 500


@app.route("/upload-and-analyze", methods=["POST"])
def upload_and_analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename or not uploaded_file.filename.strip():
        return jsonify({"error": "Empty filename"}), 400

    # Sanitize the filename to prevent directory traversal
    safe_filename = secure_filename(uploaded_file.filename)
    if not safe_filename or not safe_filename.lower().endswith(".py"):
        return jsonify({"error": "Only .py files allowed"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)

    try:
        uploaded_file.save(file_path)
        result = analyze_file(file_path)

        if result is None:
            return jsonify({"error": "Analysis failed"}), 400

        _save_and_store(result, "results/analysis_results.json", {
            "type": "file_upload_analysis",
            "file_name": safe_filename,
            "result": result,
            "created_at": datetime.utcnow()
        })
        return jsonify(result), 200

    except Exception as error:
        logger.exception("Uploaded-file analysis failed")
        return jsonify({"error": "Uploaded-file analysis could not be completed."}), 500


# ============================================================
# ANALYSIS HISTORY
# ============================================================

@app.route("/analysis-results", methods=["GET"])
def get_analysis_results():
    try:
        # Return lightweight report metadata for the history page.
        # The stored result/results fields are not modified or deleted.
        cursor = (
            analysis_collection
            .find({}, {"result": 0, "results": 0})
            .sort("created_at", -1)
            .limit(100)
        )

        reports = []
        for report in cursor:
            report["_id"] = str(report["_id"])
            reports.append(report)

        return jsonify(reports), 200

    except Exception as error:
        logger.exception("Unable to retrieve analysis history")
        return jsonify({"error": "Unable to retrieve analysis history."}), 500


@app.route("/analysis-results/<report_id>", methods=["GET"])
def get_single_analysis_result(report_id):
    # Validate the MongoDB ID before constructing ObjectId
    if not ObjectId.is_valid(report_id):
        return jsonify({"error": "Invalid report ID"}), 400

    try:
        # Retrieve the complete original report without changing its structure.
        report = analysis_collection.find_one({"_id": ObjectId(report_id)})

        if not report:
            return jsonify({"error": "Report not found"}), 404

        report["_id"] = str(report["_id"])
        return jsonify(report), 200

    except Exception as error:
        logger.exception("Unable to retrieve analysis report")
        return jsonify({"error": "Unable to retrieve the analysis report."}), 500


@app.route("/dashboard-stats", methods=["GET"])
def get_dashboard_stats():
    try:
        # Total number of analyses
        total_analyses = analysis_collection.count_documents({})

        # Calculate high-risk functions and complexity using aggregation.
        # This does not modify the stored analysis result or ML JSON schema.
        pipeline = [
            {
                "$project": {
                    "file_results": {
                        "$cond": [
                            {"$isArray": "$results"},
                            "$results",
                            {
                                "$cond": [
                                    {"$isArray": "$result.files"},
                                    "$result.files",
                                    {
                                        "$cond": [
                                            {"$ne": ["$result", None]},
                                            ["$result"],
                                            []
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            {
                "$unwind": {
                    "path": "$file_results",
                    "preserveNullAndEmptyArrays": False
                }
            },
            {
                "$project": {
                    "high_risk_count": {
                        "$size": {
                            "$ifNull": ["$file_results.high_risk_functions", []]
                        }
                    },
                    "complexity": {
                        "$ifNull": [
                            "$file_results.summary.file_cyclomatic_complexity",
                            0
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "totalHighRisk": {"$sum": "$high_risk_count"},
                    "totalComplexity": {"$sum": "$complexity"},
                    "complexityCount": {"$sum": 1}
                }
            }
        ]

        stats_result = list(analysis_collection.aggregate(pipeline))

        if stats_result:
            stats = stats_result[0]
            total_high_risk = stats.get("totalHighRisk", 0)
            total_complexity = stats.get("totalComplexity", 0)
            complexity_count = stats.get("complexityCount", 0)
        else:
            total_high_risk = 0
            total_complexity = 0
            complexity_count = 0

        # Calculate average complexity safely
        avg_complexity = (
            round(total_complexity / complexity_count, 1)
            if complexity_count > 0 else 0
        )

        # Get the latest analysis timestamp
        latest_report = analysis_collection.find_one(
            {}, {"created_at": 1}, sort=[("created_at", -1)]
        )
        latest_analysis = (
            latest_report["created_at"].isoformat()
            if latest_report and latest_report.get("created_at") else None
        )

        # Keep the existing dashboard response keys unchanged
        return jsonify({
            "totalAnalyses": total_analyses,
            "totalHighRisk": total_high_risk,
            "avgComplexity": avg_complexity,
            "latestAnalysis": latest_analysis
        }), 200

    except Exception as error:
        logger.exception("Dashboard stats request failed")
        return jsonify({"error": "Unable to retrieve dashboard statistics."}), 500


if __name__ == "__main__":
    # Run Flask development server
    app.run(
        debug=False,
        use_reloader=False
    )
