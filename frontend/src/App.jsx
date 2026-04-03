import React, { useState } from "react";
import { motion } from "framer-motion";

export default function App() {
  const [email, setEmail] = useState("");
  const [logs, setLogs] = useState([]);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const callBackend = async () => {
    if (!email) return;

    setLoading(true);
    setLogs([]);
    setResponse(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (data.logs) {
        data.logs.forEach((log, i) => {
          setTimeout(() => {
            setLogs((prev) => [...prev, log]);
          }, i * 500);
        });
      }

      setTimeout(() => {
        setResponse(data);
        setLoading(false);
      }, (data.logs?.length || 3) * 500 + 500);

    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>🚀 Accord UI</h1>

      <textarea
        rows={5}
        style={{ width: "100%" }}
        placeholder="Paste email..."
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <button onClick={callBackend}>
        {loading ? "Running..." : "Run Accord"}
      </button>

      {response && (
        <div style={{ marginTop: 20 }}>
          <h3>Draft</h3>
          <p>{response.draft}</p>

          <h4>Slots</h4>
          <ul>
            {response.slots?.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        <h3>Logs</h3>
        {logs.map((log, i) => (
          <motion.div key={i}>{log}</motion.div>
        ))}
      </div>
    </div>
  );
}