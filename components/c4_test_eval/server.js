const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const app = express();
const PORT = 3001;

const BASE_DIR = __dirname;
const REPORTS_DIR = path.join(BASE_DIR, "reports");
const EVAL_REPORT = path.join(REPORTS_DIR, "evaluation_report.json");
const PYTEST_REPORT = path.join(REPORTS_DIR, "pytest_results.json");
const COVERAGE_REPORT = path.join(REPORTS_DIR, "coverage.json");

app.use(cors());
app.use(express.json());

function readJSON(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

function buildPerFunction(covData) {
  if (!covData || !covData.files) return [];
  const rows = [];
  for (const [filePath, fileData] of Object.entries(covData.files)) {
    const fns = fileData.functions || {};
    for (const [fnName, fnData] of Object.entries(fns)) {
      if (!fnName) continue;
      const summary = fnData.summary || {};
      const covered = summary.covered_lines ?? 0;
      const total = summary.num_statements ?? 0;
      const pct = total > 0 ? Math.round((covered / total) * 100) : 100;
      rows.push({
        file: path.basename(filePath),
        function: fnName,
        covered,
        total,
        pct,
      });
    }
  }
  return rows;
}

function buildTests(pytestData) {
  if (!pytestData || !pytestData.tests) return [];
  return pytestData.tests.map((t) => {
    const callDuration = t.call?.duration ?? null;
    const durationMs = callDuration != null ? Math.round(callDuration * 1000) : null;
    // Extract readable name from nodeid: "tests/test_calculator.py::test_add_positive_numbers"
    const name = t.nodeid ? t.nodeid.split("::").pop() : t.nodeid;
    const reason =
      t.call?.longrepr
        ? String(t.call.longrepr).split("\n").slice(-1)[0].trim().slice(0, 200)
        : null;
    return {
      nodeid: t.nodeid,
      name,
      outcome: t.outcome,
      duration: durationMs,
      reason: reason || null,
    };
  });
}

app.get("/api/report", (req, res) => {
  const evalReport = readJSON(EVAL_REPORT);
  if (!evalReport) {
    return res.status(404).json({ error: "evaluation_report.json not found — run tests first." });
  }

  const pytestData = readJSON(PYTEST_REPORT);
  const coverageData = readJSON(COVERAGE_REPORT);

  const merged = {
    ...evalReport,
    tests: buildTests(pytestData),
    perFunction: buildPerFunction(coverageData),
  };

  res.json(merged);
});


app.post("/api/run", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  function send(type, message) {
    res.write(`data: ${JSON.stringify({ type, message })}\n\n`);
  }

  send("log", "Starting test pipeline...");

  const child = spawn("python", ["run.py"], { cwd: BASE_DIR, shell: true });

  child.stdout.on("data", (chunk) => {
    const lines = chunk.toString().split("\n");
    for (const line of lines) {
      if (line.trim()) send("log", line);
    }
  });

  child.stderr.on("data", (chunk) => {
    const lines = chunk.toString().split("\n");
    for (const line of lines) {
      if (line.trim()) send("log", line);
    }
  });

  child.on("close", (code) => {
    send("log", `Pipeline finished with exit code ${code}`);
    send("done", "complete");
    res.end();
  });

  child.on("error", (err) => {
    send("log", `ERROR: ${err.message}`);
    send("done", "error");
    res.end();
  });

  req.on("close", () => {
    child.kill();
  });
});


app.listen(PORT, () => {
  console.log(`\n  Test Dashboard API running at http://localhost:${PORT}`);
  console.log(`     GET  http://localhost:${PORT}/api/report`);
  console.log(`     POST http://localhost:${PORT}/api/run\n`);
});
