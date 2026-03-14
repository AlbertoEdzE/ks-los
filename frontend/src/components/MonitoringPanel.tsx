import { useEffect, useState } from "react"
import { getCorrelationId, getTraceparent, setTraceparentFromResponse } from "../lib/correlation"

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

  const load = async () => {
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/observability/summary", { headers: { "X-Correlation-ID": getCorrelationId(), "traceparent": getTraceparent() || "" } })
      if (!res.ok) throw new Error("Failed to load summary")
      const data = (await res.json()) as Summary
      setTraceparentFromResponse(res)
      setSummary(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load summary")
    }
  }

  useEffect(() => {
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
            <a href={"http://localhost:8000" + summary.drift_report_endpoint} target="_blank">Open Drift Report</a>
          </div>
        </div>
      ) : (
        <div>Loading...</div>
      )}
      {error && <div>{error}</div>}
    </div>
  )
}
