import React, { useEffect, useState } from "react";

function Dashboard() {
  const [msg, setMsg] = useState("Loading…");

  useEffect(() => {
    fetch("/ping")   // assumes the dev server proxies to the back‑end (see below)
      .then((r) => r.json())
      .then((data) => setMsg(data.msg))
      .catch((e) => setMsg(`Error: ${e.message}`));
  }, []);

  return (
    <div>
      <p>Back‑end says: <strong>{msg}</strong></p>
    </div>
  );
}

export default Dashboard;
