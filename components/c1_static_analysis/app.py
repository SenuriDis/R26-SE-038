import os
from datetime import datetime

from flask_cors import CORS

from flask import Flask, request, jsonify

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
    result = analyze_github_repository(
        repo_url,
        force_reclone=force_reclone
    )

    if "error" in result:
        return jsonify(result), 400

    # Save API result to JSON file
    save_json_to_file(
        result,
        "results/github_repo_analysis_results.json"
    )

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
    save_json_to_file(
        results,
        "results/analysis_results.json"
    )

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
    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(file_path)

    # Analyze uploaded Python file
    result = analyze_file(file_path)

    if result is None:
        return jsonify({
            "error": "Analysis failed"
        }), 400

    # Save API result to JSON file
    save_json_to_file(
        result,
        "results/analysis_results.json"
    )

    # Save result to MongoDB
    analysis_collection.insert_one({
        "type": "file_upload_analysis",
        "file_name": file.filename,
        "result": result,
        "created_at": datetime.utcnow()
    })

    return jsonify(result), 200


# ============================================================
# ANALYSIS HISTORY
# ============================================================

@app.route("/analysis-results", methods=["GET"])
def get_analysis_results():

    reports = []

    # IMPORTANT:
    # This endpoint only loads lightweight report metadata.
    #
    # The actual "result" and "results" fields are NOT deleted
    # or modified in MongoDB.
    #
    # They are simply excluded from this particular response
    # so that the history page does not download huge analysis
    # results for every report at once.

    cursor = (
        analysis_collection
        .find(
            {},
            {
                "result": 0,
                "results": 0
            }
        )
        .sort("created_at", -1)
        .limit(100)
    )

    for report in cursor:
        report["_id"] = str(report["_id"])
        reports.append(report)

    return jsonify(reports), 200


@app.route("/analysis-results/<report_id>", methods=["GET"])
def get_single_analysis_result(report_id):

    try:
        # Retrieve the COMPLETE original report.
        #
        # This includes:
        # - result
        # - results
        # - requirement_analysis
        # - risk information
        # - high-risk functions
        # - GitHub file results
        # - LLM testing context
        # - all other existing analysis output
        #
        # Nothing in the stored structure is changed.

        report = analysis_collection.find_one({
            "_id": ObjectId(report_id)
        })

        if not report:
            return jsonify({
                "error": "Report not found"
            }), 404

        # ObjectId cannot be directly serialized to JSON
        report["_id"] = str(report["_id"])

        return jsonify(report), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/dashboard-stats", methods=["GET"])
def get_dashboard_stats():

    try:
        # ---------------------------------------------------------
        # TOTAL NUMBER OF ANALYSES
        # ---------------------------------------------------------
        total_analyses = analysis_collection.count_documents({})

        # ---------------------------------------------------------
        # CALCULATE HIGH-RISK FUNCTIONS + COMPLEXITY
        # USING MONGODB AGGREGATION
        #
        # IMPORTANT:
        # This does NOT modify the stored analysis result.
        # Your original ML/analyzer JSON remains unchanged.
        # ---------------------------------------------------------

        pipeline = [
            {
                "$project": {
                    "file_results": {
                        "$cond": [
                            {
                                "$isArray": "$results"
                            },
                            "$results",

                            {
                                "$cond": [
                                    {
                                        "$isArray": "$result.files"
                                    },
                                    "$result.files",

                                    {
                                        "$cond": [
                                            {
                                                "$ne": [
                                                    "$result",
                                                    None
                                                ]
                                            },
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
                            "$ifNull": [
                                "$file_results.high_risk_functions",
                                []
                            ]
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

                    "totalHighRisk": {
                        "$sum": "$high_risk_count"
                    },

                    "totalComplexity": {
                        "$sum": "$complexity"
                    },

                    "complexityCount": {
                        "$sum": 1
                    }
                }
            }
        ]

        stats_result = list(
            analysis_collection.aggregate(pipeline)
        )

        if stats_result:

            stats = stats_result[0]

            total_high_risk = stats.get(
                "totalHighRisk",
                0
            )

            total_complexity = stats.get(
                "totalComplexity",
                0
            )

            complexity_count = stats.get(
                "complexityCount",
                0
            )

        else:

            total_high_risk = 0
            total_complexity = 0
            complexity_count = 0

        # ---------------------------------------------------------
        # AVERAGE COMPLEXITY
        # ---------------------------------------------------------

        avg_complexity = (
            round(
                total_complexity / complexity_count,
                1
            )
            if complexity_count > 0
            else 0
        )

        # ---------------------------------------------------------
        # LATEST ANALYSIS
        # ---------------------------------------------------------

        latest_report = analysis_collection.find_one(
            {},
            {
                "created_at": 1
            },
            sort=[
                ("created_at", -1)
            ]
        )

        latest_analysis = (
            latest_report["created_at"].isoformat()
            if latest_report
            and latest_report.get("created_at")
            else None
        )

        # ---------------------------------------------------------
        # RETURN DASHBOARD DATA ONLY
        # ---------------------------------------------------------

        return jsonify({
            "totalAnalyses": total_analyses,
            "totalHighRisk": total_high_risk,
            "avgComplexity": avg_complexity,
            "latestAnalysis": latest_analysis
        }), 200

    except Exception as e:

        print("Dashboard stats error:", str(e))

        return jsonify({
            "error": str(e)
        }), 500

if __name__ == "__main__":
    # Run Flask development server
    app.run(
        debug=False,
        use_reloader=False
    )


