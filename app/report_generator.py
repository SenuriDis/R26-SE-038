import json, os
from datetime import datetime

def generate_report(status, output, errors, execution_time, coverage):
    report = {
        "timestamp": str(datetime.now()),
        "status": status,
        "execution_time": execution_time,
        "coverage": coverage,
        "output": output,
        "errors": errors
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/report.json", "w") as f:
        json.dump(report, f, indent=4)

    return report