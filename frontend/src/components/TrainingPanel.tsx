import { useState } from "react"

type Plan = {
  hyperparameters: Record<string, any>
  n_samples: number
  notes: string
}

export function TrainingPanel() {
  const [loadingPlan, setLoadingPlan] = useState(false)
  const [loadingTrain, setLoadingTrain] = useState(false)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [driftUrl, setDriftUrl] = useState<string | null>(null)

  const generatePlan = async () => {
    setLoadingPlan(true)
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/training/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rationale: "Operator requested refresh" })
      })
      if (!res.ok) throw new Error("Failed to generate plan")
      const data = await res.json()
      setPlan(data.plan)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoadingPlan(false)
    }
  }

  const executeTraining = async () => {
    if (!plan) return
    setLoadingTrain(true)
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/training/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan)
      })
      if (!res.ok) throw new Error("Failed to run training")
      const data = await res.json()
      setResult(data.result)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoadingTrain(false)
    }
  }
  const runDrift = async () => {
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/training/drift", { method: "POST" })
      if (!res.ok) throw new Error("Failed to run drift")
      const data = await res.json()
      setDriftUrl("http://localhost:8000" + data.report_endpoint)
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>Training Control</h2>
      <button onClick={generatePlan} disabled={loadingPlan}>
        {loadingPlan ? "Generating plan..." : "Generate Training Plan"}
      </button>
      {plan && (
        <div>
          <pre>{JSON.stringify(plan, null, 2)}</pre>
          <button onClick={executeTraining} disabled={loadingTrain}>
            {loadingTrain ? "Running training..." : "Execute Training"}
          </button>
        </div>
      )}
      {result && (
        <div>
          <h3>Latest Training Metrics</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
          <button onClick={runDrift}>Run Drift Check</button>
          {driftUrl && (
            <div>
              <a href={driftUrl} target="_blank">Open Drift Report</a>
            </div>
          )}
        </div>
      )}
      {error && <div>{error}</div>}
    </div>
  )
}
