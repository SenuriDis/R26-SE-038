import subprocess
import sys

def run_with_coverage():
    subprocess.run([sys.executable, "-m", "coverage", "run", "-m", "pytest"], capture_output=True)
    result = subprocess.run([sys.executable, "-m", "coverage", "report"], capture_output=True, text=True)
    return result.stdout