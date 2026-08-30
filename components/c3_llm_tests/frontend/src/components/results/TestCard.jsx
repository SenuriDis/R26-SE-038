import { useState } from "react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import python from "react-syntax-highlighter/dist/esm/languages/hljs/python";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

SyntaxHighlighter.registerLanguage("python", python);

export default function TestCard({ test }) {
  const [open, setOpen] = useState(true);

  return (
    <div style={{
      background: "#1a1f2e",
      border: "1px solid #2d3748",
      borderRadius: "10px",
      marginBottom: "16px",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          borderBottom: open ? "1px solid #2d3748" : "none",
        }}
      >
        <span style={{
          fontFamily: "monospace",
          fontSize: "14px",
          color: "#93c5fd",
          fontWeight: 600,
        }}>
          {test.function_name}()
        </span>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {test.repairs > 0 && (
            <span style={{
              background: "#451a03", color: "#fcd34d",
              fontSize: "11px", fontWeight: 700,
              padding: "3px 9px", borderRadius: "20px",
            }}>
              🔧 {test.repairs} repair{test.repairs > 1 ? "s" : ""}
            </span>
          )}
          <span style={{
            background: test.is_valid ? "#064e3b" : "#7f1d1d",
            color: test.is_valid ? "#6ee7b7" : "#fca5a5",
            fontSize: "11px", fontWeight: 700,
            padding: "3px 9px", borderRadius: "20px",
          }}>
            {test.is_valid ? "✓ Valid" : "✗ Invalid"}
          </span>
          <span style={{ color: "#4b5563" }}>{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Code */}
      {open && (
        <SyntaxHighlighter
          language="python"
          style={atomOneDark}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: "12px",
            padding: "16px",
            background: "#0d1117",
          }}
        >
          {test.test_code}
        </SyntaxHighlighter>
      )}
    </div>
  );
}