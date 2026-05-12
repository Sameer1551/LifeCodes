import React, { useEffect, useState } from "react";

function Dashboard() {
  const [status, setStatus] = useState("loading");
  const [msg, setMsg] = useState("");

  const fetchData = () => {
    setStatus("loading");
    // The proxy in vite.config.js handles routing this to port 8000
    fetch("/api/ping") 
      .then((r) => {
        if (!r.ok) throw new Error("Network response was not ok");
        return r.json();
      })
      .then((data) => {
        setMsg(data.msg);
        setStatus("success");
      })
      .catch((e) => {
        setMsg(e.message);
        setStatus("error");
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="card">
      <h2>System Status</h2>
      
      {status === "loading" && <p>Loading back-end response...</p>}
      
      {status === "success" && (
        <p>
          Back-end says: <strong>{msg}</strong>
        </p>
      )}

      {status === "error" && (
        <div className="error">
          <p>Failed to connect to back-end: {msg}</p>
          <p>Ensure your Python server is running on port 8000.</p>
        </div>
      )}

      <button className="btn" onClick={fetchData} style={{ marginTop: "1rem" }}>
        Refresh Status
      </button>
    </div>
  );
}

export default Dashboard;
