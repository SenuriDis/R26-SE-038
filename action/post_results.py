"""
Turns pipeline artifacts into GitHub output.

Three things, in order of how likely they are to work:

  1. The job summary -- always written, needs no permissions.
  2. Action outputs -- for later workflow steps to branch on.
  3. A pull request comment -- best effort, and skipped politely when the
     token cannot write.

Failing to post a comment must not fail the run. The analysis is the valuable
part; a missing comment is an inconvenience, and a red check for it would
train people to ignore the check.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional

# Marks our own comment so repeated runs update it rather than piling up.
COMMENT_MARKER = "<!-- r26-se-038-ai-test-report -->"

GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def write_summary(text: str) -> None:
    """Append to the job summary, which is what shows on the run page."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError as error:
        print(f"::warning::Could not write the job summary: {error}")


def set_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    try:
        with open(output_path, "a", encoding="utf-8") as handle:
            # Delimited form, because values can span lines.
            handle.write(f"{name}<<__EOF__\n{value}\n__EOF__\n")
    except OSError as error:
        print(f"::warning::Could not set output {name}: {error}")


def _api(url: str, token: str, method: str = "GET", payload: Optional[Dict] = None):
    request = urllib.request.Request(url, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "r26-se-038-action")

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(request, data=data, timeout=30) as response:
        return json.loads(response.read().decode("utf-8") or "null")


def pull_request_number() -> Optional[int]:
    """The PR number, from the event payload Actions leaves on disk."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None

    event = load_json(Path(event_path)) or {}
    pull_request = event.get("pull_request") or {}
    number = pull_request.get("number") or event.get("number")

    return int(number) if number else None


def post_comment(body: str) -> bool:
    """
    Comment on the pull request, updating our previous comment if present.

    Returns False rather than raising -- there are several ordinary reasons
    this cannot work (a fork's read-only token, a push event with no PR).
    """
    token = os.environ.get("INPUT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    number = pull_request_number()

    if not token or not repository or not number:
        print("::notice::Not a pull request, or no token, so no comment was posted.")
        return False

    payload = {"body": f"{COMMENT_MARKER}\n{body}"}
    base = f"{GITHUB_API}/repos/{repository}"

    try:
        existing = _api(f"{base}/issues/{number}/comments?per_page=100", token) or []
        mine = next(
            (c for c in existing if COMMENT_MARKER in (c.get("body") or "")),
            None,
        )

        if mine:
            _api(f"{base}/issues/comments/{mine['id']}", token, "PATCH", payload)
            print(f"::notice::Updated the existing comment on #{number}.")
        else:
            _api(f"{base}/issues/{number}/comments", token, "POST", payload)
            print(f"::notice::Commented on #{number}.")
        return True

    except urllib.error.HTTPError as error:
        if error.code in (403, 404):
            print(
                "::warning::No permission to comment. Add "
                "`permissions: pull-requests: write` to the job, or set "
                "comment-on-pr: false."
            )
        else:
            print(f"::warning::Could not post the comment: HTTP {error.code}")
        return False
    except (urllib.error.URLError, OSError) as error:
        print(f"::warning::Could not reach the GitHub API: {error}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--pipeline-root", required=True)
    args = parser.parse_args()

    sys.path.insert(0, args.pipeline_root)
    from pipeline.report import build

    artifacts = Path(args.artifacts)
    report = build(artifacts, title="AI test analysis")

    write_summary(report)

    evaluation = load_json(artifacts / "c4_workdir" / "reports" / "evaluation_report.json") or {}
    failed = evaluation.get("test_results", {}).get("failed_tests", []) or []
    defects = [t for t in failed if t.get("failure_type") == "Real Defect"]

    c2_input = load_json(artifacts / "02_c2_input.json") or {}
    analysed = len(c2_input.get("functions", []))

    report_path = artifacts / "report.md"
    try:
        report_path.write_text(report, encoding="utf-8")
    except OSError:
        pass

    set_output("report", str(report_path))
    set_output("defects-found", str(len(defects)))
    set_output("functions-analysed", str(analysed))

    if os.environ.get("INPUT_COMMENT_ON_PR", "true").lower() == "true":
        post_comment(report)

    if defects and os.environ.get("INPUT_FAIL_ON_DEFECT", "false").lower() == "true":
        print(f"::error::{len(defects)} generated test(s) failed in a way that looks like a real defect.")
        return 1

    if analysed == 0:
        print("::notice::No functions were analysed. Nothing changed, or the path matched nothing.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
