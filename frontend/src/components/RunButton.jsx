import React, { useEffect, useRef, useState } from "react";

export default function RunButton({ running, setRunning, logLines, setLogLines, onComplete }) {
  const logRef = useRef(null);

  // Auto-scroll the log panel
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines]);

  async function handleRun() {
    setRunning(true);
    setLogLines([]);

    try {
      const res = await fetch("/api/run", { method: "POST" });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();

        for (const part of parts) {
          if (!part.startsWith("data:")) continue;
          try {
            const msg = JSON.parse(part.replace(/^data:\s*/, ""));
            if (msg.type === "log") {
              setLogLines(prev => [...prev, msg.message]);
            }
            if (msg.type === "done") {
              setRunning(false);
              onComplete();
            }
          } catch { /* malformed chunk, skip */ }
        }
      }
    } catch (err) {
      setLogLines(prev => [...prev, `ERROR: ${err.message}`]);
      setRunning(false);
    }
  }

  function lineClass(line) {
    const l = line.toLowerCase();
    if (l.includes("passed") || l.includes("pass")) return "log-line log-line--pass";
    if (l.includes("failed") || l.includes("error") || l.includes("fail")) return "log-line log-line--fail";
    if (l.startsWith("=") || l.startsWith("[")) return "log-line log-line--head";
    return "log-line";
  }

  return (
    <div className="card section run-area fade-up" style={{ animationDelay: ".06s" }}>
      <div className="run-actions">
        <button
          id="run-tests-btn"
          className={`run-btn${running ? " run-btn--running" : ""}`}
          onClick={handleRun}
          disabled={running}
        >
          {running ? " Running…" : "Run Tests Now"}
        </button>
        <span className="run-hint">
          {running
            ? "Executing pytest + coverage — results stream below"
            : "Triggers python run.py and streams live output"}
        </span>
      </div>

      {logLines.length > 0 && (
        <div className="log-panel" ref={logRef} id="live-log-panel">
          {logLines.map((line, i) => (
            <div key={i} className={lineClass(line)}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}
