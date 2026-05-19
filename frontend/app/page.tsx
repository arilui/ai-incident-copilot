"use client";

import { useState } from "react";
import { AlertTriangle, Activity, Wrench, Upload } from "lucide-react";

export default function Home() {
  const [logs, setLogs] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (!file) return;

    const text = await file.text();
    setLogs(text);
  };

  const analyzeLogs = async () => {
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ logs }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-5xl font-bold mb-2">
            AI Incident Copilot
          </h1>
          <p className="text-zinc-400 text-lg">
            Analyze CI/CD failures and generate incident reports.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
            <h2 className="text-2xl font-semibold mb-4">
              Pipeline Logs
            </h2>

            <label className="mb-4 flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-zinc-700 bg-zinc-950 p-4 text-center hover:bg-zinc-900 transition">
              <Upload size={18} />
              <input
                type="file"
                accept=".txt,.log"
                onChange={handleFileUpload}
                className="hidden"
              />
              <span className="text-sm text-zinc-300">
                Upload a .txt or .log file
              </span>
            </label>

            <textarea
              value={logs}
              onChange={(e) => setLogs(e.target.value)}
              placeholder="Paste CI/CD logs here..."
              className="w-full h-96 bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-sm font-mono resize-none outline-none"
            />

            <button
              onClick={analyzeLogs}
              disabled={loading}
              className="mt-4 w-full bg-white text-black font-semibold py-3 rounded-xl hover:bg-zinc-200 transition disabled:opacity-60"
            >
              {loading ? "Analyzing..." : "Analyze Incident"}
            </button>
          </div>

          <div className="space-y-6">
            <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle />
                <h2 className="text-2xl font-semibold">
                  Incident Summary
                </h2>
              </div>

              {result ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-zinc-400 text-sm">Severity</p>
                    <p className="text-xl font-bold capitalize">
                      {result.severity}
                    </p>
                  </div>

                  <div>
                    <p className="text-zinc-400 text-sm">Likely Stage</p>
                    <p className="text-xl font-bold capitalize">
                      {result.likely_stage}
                    </p>
                  </div>

                  <div>
                    <p className="text-zinc-400 text-sm">Summary</p>
                    <p>{result.summary}</p>
                  </div>

                  <div>
                    <p className="text-zinc-400 text-sm">Analysis Mode</p>
                    <p className="text-sm uppercase tracking-wide">
                      {result.analysis_mode}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-zinc-500">
                  No analysis yet.
                </p>
              )}
            </div>

            <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
              <div className="flex items-center gap-2 mb-4">
                <Activity />
                <h2 className="text-2xl font-semibold">
                  Top Errors
                </h2>
              </div>

              {result?.top_errors?.length > 0 ? (
                <div className="space-y-2">
                  {result.top_errors.map(
                    (error: string, index: number) => (
                      <div
                        key={index}
                        className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-sm font-mono"
                      >
                        {error}
                      </div>
                    )
                  )}
                </div>
              ) : (
                <p className="text-zinc-500">
                  No errors detected.
                </p>
              )}
            </div>

            <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
              <div className="flex items-center gap-2 mb-4">
                <Wrench />
                <h2 className="text-2xl font-semibold">
                  Suggested Fix
                </h2>
              </div>

              <p>
                {result?.suggested_fix ||
                  "No recommendations yet."}
              </p>
            </div>

            {result?.postmortem && (
              <div className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800">
                <h2 className="text-2xl font-semibold mb-4">
                  Postmortem Draft
                </h2>

                <div className="space-y-3 text-sm">
                  <div>
                    <p className="text-zinc-400">Title</p>
                    <p>{result.postmortem.title}</p>
                  </div>

                  <div>
                    <p className="text-zinc-400">Impact</p>
                    <p>{result.postmortem.impact}</p>
                  </div>

                  <div>
                    <p className="text-zinc-400">Root Cause</p>
                    <p>{result.postmortem.root_cause}</p>
                  </div>

                  <div>
                    <p className="text-zinc-400">Resolution</p>
                    <p>{result.postmortem.resolution}</p>
                  </div>

                  <div>
                    <p className="text-zinc-400">Prevention</p>
                    <p>{result.postmortem.prevention}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}