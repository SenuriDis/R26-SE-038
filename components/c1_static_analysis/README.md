# Static Code Analysis Component

### Intelligent Software Testing System Research Project

Developed by:

- **Senuri Dissanayake**
- **IT22210692**

---

# Project Overview

The Static Code Analysis Component is an AI-enhanced software analysis module developed for the Intelligent Software Testing System research project.

This component performs structural source code analysis using Python Abstract Syntax Tree (AST) techniques to identify complexity hotspots, dependency relationships, high-risk functions, and intelligent software testing opportunities.

The system also generates AI-oriented testing recommendations to assist software developers and testers in prioritizing testing activities.

---

# Key Features

## Static Code Analysis

- Python AST parsing
- Cyclomatic complexity calculation
- Nesting depth analysis
- Control flow analysis
- Dependency extraction
- Function-level analysis

---

## Risk Detection

- High-risk function identification
- Structural risk categorization
- Complexity hotspot detection
- Dependency-based risk evaluation

---

## Intelligent Testing Recommendations

The component introduces an intelligent recommendation mechanism that generates:

- Risk-aware testing suggestions
- Priority-based testing guidance
- AI-ready testing context
- Function-specific testing focus areas

---

## Repository / Folder Analysis

- Analyze complete Python repositories
- Multi-file analysis support
- Repository-level complexity overview
- Folder-level risk visualization

---

## Historical Report Management

- MongoDB Atlas integration
- Saved analysis history
- Reopen previous analysis reports
- Stored repository analysis results

---

# Technologies Used

## Frontend Technologies

- React.js
- Vite
- Tailwind CSS
- Axios
- Lucide React Icons

---

## Backend Technologies

- Python
- Flask
- Flask-CORS
- PyMongo
- AST (Abstract Syntax Tree)

---

## Database

- MongoDB Atlas

---

# System Workflow

1. User uploads a Python file or enters a repository folder path
2. Backend parses source code using AST
3. Structural metrics are extracted
4. Risk analysis is performed
5. Intelligent testing recommendations are generated
6. Results are stored in MongoDB Atlas
7. Frontend visualizes analysis results

---

# Folder Structure

```bash
frontend/
│
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── App.jsx
│
backend/
│
├── src/
│   ├── parser/
│   ├── extractor/
│   ├── metrics/
│   ├── intelligence/
│   ├── risk/
│   ├── output/
│   └── config/
│
├── app.py
├── main.py
└── requirements.txt