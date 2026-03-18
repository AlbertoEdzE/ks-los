import { useEffect, useState } from "react"
import { getCorrelationId, getTraceparent, setTraceparentFromResponse } from "../lib/correlation"

const ADMIN_HEADERS = { Authorization: "Bearer admin-access" }

type Summary = {
  training_runs: number
  drift_runs: number
  risk_inferences: number
  mlflow_url: string
  drift_report_endpoint: string
}

export function MonitoringPanel() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setError(null)
      try {
        const res = await fetch("http://localhost:8000/observability/summary", { headers: { ...ADMIN_HEADERS, "X-Correlation-ID": getCorrelationId(), "traceparent": getTraceparent() || "" } })
        if (!res.ok) throw new Error("Failed to load summary")
        const data = (await res.json()) as Summary
        setTraceparentFromResponse(res)
        setSummary(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load summary")
      }
    }

    load()
  }, [])

  return (
    <div>
      <h2>Monitoring</h2>
      {summary ? (
        <div>
          <div>Training Runs: {summary.training_runs}</div>
          <div>Drift Runs: {summary.drift_runs}</div>
          <div>Risk Inferences: {summary.risk_inferences}</div>
          <div>
            <a href={summary.mlflow_url} target="_blank">Open MLflow</a>
          </div>
          <div>
            <button
              onClick={async () => {
                const res = await fetch("http://localhost:8000" + summary.drift_report_endpoint, { headers: ADMIN_HEADERS })
                if (!res.ok) return
                const html = await res.text()
                const blob = new Blob([html], { type: "text/html" })
                const url = URL.createObjectURL(blob)
                window.open(url, "_blank", "noopener,noreferrer")
                setTimeout(() => URL.revokeObjectURL(url), 60_000)
              }}
            >
              Open Drift Report
            </button>
          </div>
        </div>
      ) : (
        <div>Loading...</div>
      )}
      {error && <div>{error}</div>}
    </div>
  )
}
