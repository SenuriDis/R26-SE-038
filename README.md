# Test Execution and Evaluation Component
**Project:** LLM and ML Enhanced Software Testing System for Automatic Test Case Generation and Code Quality Review  
**Student:** Premaratne R.A.N.C — IT22050908  
**Project ID:** R26-SE-038

---

## Overview

This component is responsible for:
- Executing automatically generated unit test cases
- Running them inside Docker sandbox containers (isolated environment)
- Measuring code coverage (statement, branch, function level)
- Generating structured JSON evaluation reports
- Providing pass/fail rates and quality grades

---

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Evaluation Pipeline
```bash
python run.py
```

### 3. Run with Docker (Sandboxed)
```bash
docker build -t test-eval .
docker run --rm test-eval
```

### 4. Run PyTest manually
```bash
python -m pytest tests/ -v
```

---

## Technologies Used

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Primary implementation language |
| PyTest | Test execution framework |
| Coverage.py | Code coverage measurement |
| pytest-json-report | Structured pass/fail JSON output |
| Docker | Sandboxed isolated execution environment |
| JSON | Structured report format for CI/CD integration |