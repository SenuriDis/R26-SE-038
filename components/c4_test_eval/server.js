const crypto = require("crypto");
const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const app = express();
const PORT = Number(process.env.PORT || 8004);
const BASE_DIR = __dirname;
const REPORTS_DIR = path.join(BASE_DIR, "reports");
const SANDBOX_ROOT = process.env.SANDBOX_ROOT || "/sandbox";
const SANDBOX_VOLUME = process.env.C4_SANDBOX_VOLUME || "r26-se038-c4-sandbox";
const EVALUATOR_IMAGE = process.env.C4_EVALUATOR_IMAGE || "r26-se038-c4:local";
const MAX_INPUT_BYTES = 20 * 1024 * 1024;
const EVALUATION_TIMEOUT_MS = 30 * 60 * 1000;

app.use(cors());
app.use(express.json({ limit: "25mb" }));

class RequestError extends Error {}

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
    for (const [functionName, functionData] of Object.entries(fileData.functions || {})) {
      if (!functionName) continue;
      const summary = functionData.summary || {};
      const covered = summary.covered_lines ?? 0;
      const total = summary.num_statements ?? 0;
      rows.push({
        file: path.basename(filePath),
        function: functionName,
        covered,
        total,
        pct: total > 0 ? Math.round((covered / total) * 100) : 100,
      });
    }
  }
  return rows;
}

function buildTests(pytestData) {
  if (!pytestData || !pytestData.tests) return [];
  return pytestData.tests.map((test) => {
    const duration = test.call?.duration ?? null;
    const reason = test.call?.longrepr
      ? String(test.call.longrepr).split("\n").slice(-1)[0].trim().slice(0, 200)
      : null;
    return {
      nodeid: test.nodeid,
      name: test.nodeid ? test.nodeid.split("::").pop() : test.nodeid,
      outcome: test.outcome,
      duration: duration == null ? null : Math.round(duration * 1000),
      reason: reason || null,
    };
  });
}

function validateFileMap(files, field) {
  if (!files || typeof files !== "object" || Array.isArray(files)) {
    throw new RequestError(`${field} must be an object of relative .py paths to source text.`);
  }

  const entries = Object.entries(files);
  if (!entries.length) {
    throw new RequestError(`${field} must contain at least one Python file.`);
  }

  let totalBytes = 0;
  return entries.map(([name, contents]) => {
    const relativePath = name.replace(/\\/g, "/");
    const segments = relativePath.split("/");
    if (
      !relativePath ||
      relativePath.startsWith("/") ||
      segments.some((segment) => !segment || segment === "." || segment === "..") ||
      path.posix.extname(relativePath) !== ".py"
    ) {
      throw new RequestError(`${field} contains an invalid Python file path: ${name}`);
    }
    if (typeof contents !== "string") {
      throw new RequestError(`${field}[${JSON.stringify(name)}] must be a string.`);
    }

    totalBytes += Buffer.byteLength(contents, "utf8");
    if (totalBytes > MAX_INPUT_BYTES) {
      throw new RequestError(`${field} exceeds the ${MAX_INPUT_BYTES} byte limit.`);
    }
    return [relativePath, contents];
  });
}

function writeFiles(root, files) {
  for (const [relativePath, contents] of files) {
    const destination = path.resolve(root, relativePath);
    if (!destination.startsWith(`${path.resolve(root)}${path.sep}`)) {
      throw new RequestError(`Invalid file path: ${relativePath}`);
    }
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, contents, "utf8");
  }
}

function runDocker(args, containerName, onOutput) {
  return new Promise((resolve, reject) => {
    const child = spawn("docker", args, { stdio: ["ignore", "pipe", "pipe"] });
    let output = "";
    let timedOut = false;
    let settled = false;

    const append = (stream, chunk) => {
      const text = chunk.toString();
      output = (output + text).slice(-2 * 1024 * 1024);
      onOutput(text);
      stream.write(text);
    };

    const timeout = setTimeout(() => {
      timedOut = true;
      child.kill();
      const cleanup = spawn("docker", ["rm", "--force", containerName], {
        stdio: "ignore",
      });
      cleanup.unref();
    }, EVALUATION_TIMEOUT_MS);

    child.stdout.on("data", (chunk) => append(process.stdout, chunk));
    child.stderr.on("data", (chunk) => append(process.stderr, chunk));
    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      reject(new Error(`Could not start Docker evaluator: ${error.message}`));
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (timedOut) {
        reject(new Error("C4 evaluation exceeded the 30 minute timeout."));
      } else {
        resolve({ exitCode: code, output });
      }
    });
  });
}

async function evaluateFiles(payload, onOutput = () => {}) {
  const sourceFiles = validateFileMap(payload.source_files, "source_files");
  const testFiles = validateFileMap(payload.test_files, "test_files");
  const conftest = payload.conftest ?? sourceFiles.find(([name]) => name === "conftest.py")?.[1];
  if (conftest !== undefined && typeof conftest !== "string") {
    throw new RequestError("conftest must be a string when provided.");
  }
  const runId = crypto.randomUUID();
  const workspace = path.join(SANDBOX_ROOT, runId);
  const containerName = `r26-c4-${runId.slice(0, 12)}`;
  const sourceRoot = path.join(workspace, "src");
  const testsRoot = path.join(workspace, "tests");
  const reportsRoot = path.join(workspace, "reports");

  fs.mkdirSync(sourceRoot, { recursive: true });
  fs.mkdirSync(testsRoot, { recursive: true });
  fs.mkdirSync(reportsRoot, { recursive: true });

  try {
    writeFiles(sourceRoot, sourceFiles);
    writeFiles(testsRoot, testFiles);
    fs.copyFileSync(path.join(BASE_DIR, "execute_tests.py"), path.join(workspace, "execute_tests.py"));
    if (conftest !== undefined) {
      fs.writeFileSync(path.join(workspace, "conftest.py"), conftest, "utf8");
    }

    const args = [
      "run", "--rm",
      "--name", containerName,
      "--network", "none",
      "--cap-drop", "ALL",
      "--security-opt", "no-new-privileges",
      "--pids-limit", "256",
      "--memory", "2g",
      "--cpus", "2",
      "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
      "--mount", `type=volume,source=${SANDBOX_VOLUME},target=/sandbox`,
      "--workdir", workspace,
      "--env", `PYTHONPATH=${sourceRoot}`,
      "--env", "PYTHONIOENCODING=utf-8",
      "--env", "PYTHONUTF8=1",
      "--entrypoint", "python",
      EVALUATOR_IMAGE,
      path.join(workspace, "execute_tests.py"),
    ];

    const execution = await runDocker(args, containerName, onOutput);
    const reportPath = path.join(reportsRoot, "evaluation_report.json");
    if (!fs.existsSync(reportPath)) {
      throw new Error(
        `C4 did not produce an evaluation report (Docker exit code ${execution.exitCode}).\n${execution.output.slice(-4000)}`
      );
    }

    const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    for (const name of [
      "evaluation_report.json",
      "pytest_results.json",
      "coverage.json",
      "execution.log",
      "mutation.log",
    ]) {
      const from = path.join(reportsRoot, name);
      if (fs.existsSync(from)) {
        fs.copyFileSync(from, path.join(REPORTS_DIR, name));
      }
    }

    const qualityGrade = report.evaluation_summary?.quality_grade || null;
    return {
      grade: /^[ABCD]/.test(qualityGrade || "") ? qualityGrade[0] : null,
      quality_grade: qualityGrade,
      execution_status: report.execution_status,
      test_results: report.test_results,
      report,
      evaluator_exit_code: execution.exitCode,
      evaluator_output: execution.output.slice(-12000),
    };
  } finally {
    fs.rmSync(workspace, { recursive: true, force: true });
  }
}

function collectPythonFiles(root, relativeRoot = root) {
  const files = {};
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (![".git", ".venv", "venv", "__pycache__", "node_modules"].includes(entry.name)) {
        Object.assign(files, collectPythonFiles(path.join(root, entry.name), relativeRoot));
      }
    } else if (entry.isFile() && entry.name.endsWith(".py")) {
      const fullPath = path.join(root, entry.name);
      const relativePath = path.relative(relativeRoot, fullPath).split(path.sep).join("/");
      files[relativePath] = fs.readFileSync(fullPath, "utf8");
    }
  }
  return files;
}

app.get("/api/report", (req, res) => {
  const evalReport = readJSON(path.join(REPORTS_DIR, "evaluation_report.json"));
  if (!evalReport) {
    return res.status(404).json({ error: "evaluation_report.json not found — run tests first." });
  }

  const pytestData = readJSON(path.join(REPORTS_DIR, "pytest_results.json"));
  const coverageData = readJSON(path.join(REPORTS_DIR, "coverage.json"));
  res.json({
    ...evalReport,
    tests: buildTests(pytestData),
    perFunction: buildPerFunction(coverageData),
  });
});

app.post("/api/evaluate", async (req, res) => {
  try {
    const result = await evaluateFiles(req.body);
    res.json(result);
  } catch (error) {
    const status = error instanceof RequestError ? 400 : 500;
    res.status(status).json({ error: error.message });
  }
});

app.post("/api/run", async (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const send = (type, message) => {
    res.write(`data: ${JSON.stringify({ type, message })}\n\n`);
  };

  send("log", "Starting isolated test evaluation...");
  try {
    const result = await evaluateFiles({
      source_files: collectPythonFiles(path.join(BASE_DIR, "src")),
      test_files: collectPythonFiles(path.join(BASE_DIR, "tests")),
      conftest: fs.readFileSync(path.join(BASE_DIR, "conftest.py"), "utf8"),
    }, (chunk) => send("log", chunk));
    send("log", `Evaluation finished with grade ${result.grade || "unavailable"}.`);
    send("done", "complete");
  } catch (error) {
    send("log", `ERROR: ${error.message}`);
    send("done", "error");
  } finally {
    res.end();
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`C4 Test Evaluation API running at http://localhost:${PORT}`);
  console.log(`  GET  http://localhost:${PORT}/api/report`);
  console.log(`  POST http://localhost:${PORT}/api/evaluate`);
  console.log(`  POST http://localhost:${PORT}/api/run`);
});
