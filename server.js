const express = require("express");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const app = express();
const BASE_DIR = __dirname;
const REPORTS = path.join(BASE_DIR, "reports");

app.use(express.json());

// GET /api/report
app.get("/api/report", (req, res) => {
  try {
    const evalPath = path.join(REPORTS, "evaluation_report.json");
    const pytestPath = path.join(REPORTS, "pytest_results.json");
    const covPath = path.join(REPORTS, "coverage.json");

    if (!fs.existsSync(evalPath)) {
      return res.status(404).json({ error: "No report found. Run tests first." });
    }

    const report = JSON.parse(fs.readFileSync(evalPath,   "utf-8"));
    const pytest = fs.existsSync(pytestPath)
      ? JSON.parse(fs.readFileSync(pytestPath, "utf-8"))
      : null;
    const coverage = fs.existsSync(covPath)
      ? JSON.parse(fs.readFileSync(covPath, "utf-8"))
      : null;

    // Per-test detail list
    const tests = pytest?.tests?.map(t => ({
      name: t.nodeid.split("::").pop(),
      nodeid: t.nodeid,
      outcome: t.outcome,
      duration: Math.round(
        ((t.setup?.duration || 0) + (t.call?.duration || 0) + (t.teardown?.duration || 0)) * 1000
      ),
      reason: t.call?.longrepr
        ? String(t.call.longrepr).split("\n").slice(-3).join(" ").trim().slice(0, 200)
        : null,
    })) ?? [];

    // Per-function coverage
    const files = coverage?.files ?? {};
    const perFunction = [];
    for (const [file, fileData] of Object.entries(files)) {
      const fns = fileData.functions ?? {};
      for (const [fn, fnData] of Object.entries(fns)) {
        if (!fn) continue; // skip module-level blank key
        perFunction.push({
          file: path.basename(file),
          function: fn,
          covered: fnData.summary.covered_lines,
          total: fnData.summary.num_statements,
          pct: Math.round(fnData.summary.percent_covered),
        });
      }
    }

    res.json({ ...report, tests, perFunction });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


app.post("/api/run", (req, res) => {
  res.setHeader("Content-Type",  "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection",    "keep-alive");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.flushHeaders();

  const send = (data) => res.write(`data: ${JSON.stringify(data)}\n\n`);

  send({ type: "start", message: "Starting test run…" });

  const child = spawn("python", ["run.py"], {
    cwd:   BASE_DIR,
    shell: true,
  });

  child.stdout.on("data", (chunk) => {
    chunk.toString().split("\n").forEach(line => {
      if (line.trim()) send({ type: "log", message: line });
    });
  });

  child.stderr.on("data", (chunk) => {
    chunk.toString().split("\n").forEach(line => {
      if (line.trim()) send({ type: "log", message: line });
    });
  });

  child.on("close", (code) => {
    send({ type: "done", exitCode: code });
    res.end();
  });

  req.on("close", () => child.kill());
});

const PORT = 3001;
app.listen(PORT, () =>
  console.log(`\n Test Dashboard API  →  http://localhost:${PORT}\n`)
);
