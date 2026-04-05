import React, { useState, useEffect, useRef, useCallback } from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };

// --- Types ---
interface TrainingPlan {
  hyperparameters: Record<string, unknown>;
  n_samples: number;
  notes: string;
}

interface TrainingResult {
  accuracy: number;
  auc: number;
  precision: number;
  recall: number;
  f1: number;
  confusion_matrix: number[][];
  model_uri: string;
  run_id: string;
  dataset_size: number;
  train_size: number;
  test_size: number;
}

interface BatchTestResult {
  input: {
    credit_score?: number;
    total_debt?: number;
    [key: string]: unknown;
  };
  prediction: number;
  probability: number;
  risk_level: string;
}

interface TrainingStatus {
  is_training: boolean;
  progress: number;
  status: string;
  logs: string[];
  result: TrainingResult | null;
  error: string | null;
  duration: number;
}

interface CurrentModelMetrics {
  version: string;
  stage: string;
  run_id: string;
  creation_timestamp: number;
  metrics: {
    accuracy: number;
    auc: number;
    precision: number;
    recall: number;
    f1: number;
    [key: string]: number;
  };
}

// --- Components ---

const ProgressBar: React.FC<{ progress: number; status: string }> = ({ progress, status }) => (
  <div style={{ width: '100%', marginBottom: '16px' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
      <span style={{ fontWeight: '500', color: '#4a5568' }}>{status}</span>
      <span style={{ fontWeight: '600', color: '#3182ce' }}>{progress}%</span>
    </div>
    <div style={{ width: '100%', height: '12px', backgroundColor: '#edf2f7', borderRadius: '6px', overflow: 'hidden' }}>
      <div style={{ 
        width: `${progress}%`, 
        height: '100%', 
        backgroundColor: '#3182ce', 
        transition: 'width 0.3s ease' 
      }} />
    </div>
  </div>
);

const MetricsCard: React.FC<{ label: string; value: string | number; color?: string }> = ({ label, value, color = '#2d3748' }) => (
  <div style={{ padding: '16px', backgroundColor: '#f7fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
    <div style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color }}>{value}</div>
  </div>
);

const ConfusionMatrix: React.FC<{ matrix: number[][] }> = ({ matrix }) => {
  if (!matrix || matrix.length !== 2) return null;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr', gap: '4px', textAlign: 'center', fontSize: '0.875rem' }}>
      <div></div>
      <div style={{ fontWeight: 'bold' }}>Pred 0</div>
      <div style={{ fontWeight: 'bold' }}>Pred 1</div>
      
      <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>Actual 0</div>
      <div style={{ padding: '12px', backgroundColor: '#e6fffa', border: '1px solid #b2f5ea' }}>TN: {matrix[0][0]}</div>
      <div style={{ padding: '12px', backgroundColor: '#fff5f5', border: '1px solid #fed7d7' }}>FP: {matrix[0][1]}</div>
      
      <div style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>Actual 1</div>
      <div style={{ padding: '12px', backgroundColor: '#fff5f5', border: '1px solid #fed7d7' }}>FN: {matrix[1][0]}</div>
      <div style={{ padding: '12px', backgroundColor: '#e6fffa', border: '1px solid #b2f5ea' }}>TP: {matrix[1][1]}</div>
    </div>
  );
};

export const TrainingPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'current' | 'train'>('current');
  const [activeStep, setActiveStep] = useState(1);
  const [currentMetrics, setCurrentMetrics] = useState<CurrentModelMetrics | null>(null);
  
  // Step 1: Configuration
  const [rationale, setRationale] = useState('Periodic refresh to improve AUC and stability');
  const [nSamples, setNSamples] = useState(2000);
  const [noiseLevel, setNoiseLevel] = useState(0.1);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [plan, setPlan] = useState<TrainingPlan | null>(null);

  // Step 2: Execution
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const pollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // Step 4: Testing
  const [testInput, setTestInput] = useState('{\n  "age": 35,\n  "credit_score": 720,\n  "utilization_ratio": 0.3,\n  "total_debt": 5000,\n  "history_length_months": 48,\n  "derogatory_marks": 0,\n  "thin_file_flag": 0\n}');
  const [testResults, setTestResults] = useState<BatchTestResult[]>([]);

  // Step 5: Deployment
  const [deployStatus, setDeployStatus] = useState<'idle' | 'deploying' | 'deployed' | 'failed'>('idle');
  const [rollbackStatus, setRollbackStatus] = useState<'idle' | 'rolling_back' | 'rolled_back' | 'failed'>('idle');
  const [rollbackMessage, setRollbackMessage] = useState<string | null>(null);

  const fetchCurrentMetrics = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/training/metrics', { headers: ADMIN_HEADERS });
      if (res.ok) {
        const data = await res.json();
        if (data.status && data.status !== 'success' && !data.metrics) {
           setCurrentMetrics(null);
        } else {
           setCurrentMetrics(data);
        }
      }
    } catch (e) {
      console.error("Failed to fetch metrics", e);
    }
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  // Fetch current metrics on mount
  useEffect(() => {
    fetchCurrentMetrics();
  }, [fetchCurrentMetrics]);

  const generatePlan = async () => {
    setIsGeneratingPlan(true);
    try {
      const res = await fetch('http://localhost:8000/training/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...ADMIN_HEADERS },
        body: JSON.stringify({ rationale, n_samples: nSamples, noise_level: noiseLevel })
      });
      if (res.ok) {
        const data = await res.json();
        setPlan(data.plan);
      } else {
        const err = await res.json();
        alert(`Failed to generate plan: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert('Failed to generate plan: Network or Server Error');
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  const startTraining = async () => {
    if (!plan) return;
    try {
      const res = await fetch('http://localhost:8000/training/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...ADMIN_HEADERS },
        body: JSON.stringify(plan)
      });
      if (res.ok) {
        setActiveStep(2);
        startPolling();
      } else {
        const err = await res.json();
        alert(`Failed to start: ${err.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert('Error starting training');
    }
  };

  const startPolling = () => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    pollInterval.current = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/training/status', { headers: ADMIN_HEADERS });
        if (res.ok) {
          const data: TrainingStatus = await res.json();
          setStatus(data);
          
          if (data.status === 'completed' || data.status === 'failed') {
            if (pollInterval.current) clearInterval(pollInterval.current);
            if (data.status === 'completed') {
               // Auto advance to Analysis after short delay? No, let user click.
               // Also refresh current metrics if deployed? No, deployment is manual step 5.
            }
          }
        }
      } catch (e) {
        console.error('Polling error', e);
      }
    }, 1000);
  };

  const runBatchTest = async () => {
    try {
      const samples = JSON.parse(`[${testInput}]`);
      const res = await fetch('http://localhost:8000/training/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...ADMIN_HEADERS },
        body: JSON.stringify({ samples })
      });
      if (res.ok) {
        const data = await res.json();
        setTestResults(Array.isArray(data.results) ? (data.results as BatchTestResult[]) : []);
      }
    } catch {
      alert('Invalid JSON input or API error');
    }
  };

  const deployModel = async () => {
    setDeployStatus('deploying');
    try {
      const res = await fetch('http://localhost:8000/model/reload', { method: 'POST', headers: ADMIN_HEADERS });
      if (res.ok) {
        setDeployStatus('deployed');
        alert('Model successfully deployed to production!');
        fetchCurrentMetrics(); // Refresh metrics tab
      } else {
        setDeployStatus('failed');
      }
    } catch {
      setDeployStatus('failed');
    }
  };

  const rollbackModel = async () => {
    setRollbackStatus('rolling_back');
    try {
      const res = await fetch('http://localhost:8000/model/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...ADMIN_HEADERS },
      });
      const data = await res.json();
      if (res.ok) {
        setRollbackStatus('rolled_back');
        setRollbackMessage(data.message);
        fetchCurrentMetrics(); // Refresh metrics tab
      } else {
        setRollbackStatus('failed');
        setRollbackMessage(data.detail || 'Failed to rollback');
      }
    } catch {
      setRollbackStatus('failed');
      setRollbackMessage('Network error');
    }
  };

  // --- Render Steps ---

  const renderCurrentMetrics = () => {
    if (!currentMetrics) {
        return (
            <div style={{ textAlign: 'center', padding: '48px', color: '#718096' }}>
                <div style={{ fontSize: '1.2rem', marginBottom: '16px' }}>No Active Model Found</div>
                <p>Train a new model to see metrics here.</p>
                <button 
                    onClick={() => setActiveTab('train')}
                    style={{ marginTop: '24px', padding: '10px 24px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    Start Training
                </button>
            </div>
        );
    }

    const m = currentMetrics.metrics;
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#2d3748' }}>Active Model Performance</h3>
                <div style={{ fontSize: '0.875rem', color: '#718096' }}>
                    Version: <span style={{ fontWeight: 'bold', color: '#2d3748' }}>{currentMetrics.version}</span> | 
                    Run ID: <span style={{ fontFamily: 'monospace' }}>{currentMetrics.run_id.substring(0, 8)}...</span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
                <MetricsCard label="Accuracy" value={m.accuracy ? (m.accuracy * 100).toFixed(2) + '%' : '-'} color="#38a169" />
                <MetricsCard label="AUC" value={m.auc ? m.auc.toFixed(4) : '-'} color="#3182ce" />
                <MetricsCard label="Precision" value={m.precision ? m.precision.toFixed(4) : '-'} />
                <MetricsCard label="Recall" value={m.recall ? m.recall.toFixed(4) : '-'} />
                <MetricsCard label="F1 Score" value={m.f1 ? m.f1.toFixed(4) : '-'} />
            </div>

            <div style={{ padding: '24px', backgroundColor: '#ebf8ff', borderRadius: '8px', border: '1px solid #bee3f8' }}>
                <h4 style={{ fontWeight: '600', color: '#2c5282', marginBottom: '8px' }}>Model Status: Active</h4>
                <p style={{ color: '#4a5568', fontSize: '0.9rem' }}>
                    This model is currently serving all inference requests. 
                    If performance is degrading, consider retraining.
                </p>
                <button 
                    onClick={() => setActiveTab('train')}
                    style={{ marginTop: '16px', padding: '10px 20px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                >
                    Train New Version
                </button>
            </div>
        </div>
    );
  };

  const renderStep1 = () => (
    <div>
      <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>Configuration & Planning</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <div>
          <label htmlFor="rationale" style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>Rationale / Strategy</label>
          <textarea 
            id="rationale"
            value={rationale} 
            onChange={e => setRationale(e.target.value)}
            style={{ width: '100%', height: '100px', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e0' }}
          />
        </div>
        <div>
          <label htmlFor="nSamples" style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>Synthetic Dataset Size</label>
          <input 
            id="nSamples"
            type="number" 
            value={nSamples} 
            onChange={e => setNSamples(parseInt(e.target.value))}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e0', marginBottom: '16px' }}
          />
          <label htmlFor="noiseLevel" style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>Noise Level (0.0 - 1.0)</label>
          <input 
            id="noiseLevel"
            type="number" 
            step="0.1"
            value={noiseLevel} 
            onChange={e => setNoiseLevel(parseFloat(e.target.value))}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e0' }}
          />
        </div>
      </div>
      
      <button 
        onClick={generatePlan} 
        disabled={isGeneratingPlan}
        style={{ padding: '10px 20px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
      >
        {isGeneratingPlan ? 'Generating...' : 'Generate Training Plan'}
      </button>

      {plan && (
        <div className="mt-6 rounded-3xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5">
          <h4 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Proposed Plan</h4>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(plan as unknown as Record<string, unknown>).slice(0, 10).map(([k, v]) => (
              <div key={k} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] px-4 py-3">
                <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider break-all">{k}</div>
                <div className="mt-1 text-sm text-slate-800 dark:text-slate-200 break-words">{typeof v === 'object' ? 'View details below' : String(v)}</div>
              </div>
            ))}
          </div>
          <details className="mt-4">
            <summary className="cursor-pointer text-xs font-semibold text-slate-600 dark:text-slate-300">View raw JSON</summary>
            <pre className="mt-3 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[240px] overflow-auto">
              {JSON.stringify(plan, null, 2)}
            </pre>
          </details>
          <button 
            onClick={startTraining}
            style={{ marginTop: '16px', padding: '10px 20px', backgroundColor: '#38a169', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
          >
            Approve & Start Training
          </button>
        </div>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div>
      <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>Training Execution</h3>
      {status && (
        <>
          <ProgressBar progress={status.progress} status={status.status} />
          
          <div style={{ height: '300px', overflowY: 'auto', backgroundColor: '#1a202c', color: '#a0aec0', padding: '16px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.875rem' }}>
            {status.logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
            {status.logs.length === 0 && <div>Waiting for logs...</div>}
          </div>

          {status.status === 'completed' && (
            <div style={{ marginTop: '24px', textAlign: 'right' }}>
               <button 
                onClick={() => setActiveStep(3)}
                style={{ padding: '10px 20px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
              >
                Proceed to Analysis
              </button>
            </div>
          )}
        </>
      )}
      {!status && <div>Starting...</div>}
    </div>
  );

  const renderStep3 = () => {
    if (!status?.result) return <div>No results available.</div>;
    const r = status.result;
    return (
      <div>
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>Analysis Dashboard</h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
          <MetricsCard label="Accuracy" value={(r.accuracy * 100).toFixed(2) + '%'} color="#38a169" />
          <MetricsCard label="AUC" value={r.auc.toFixed(4)} color="#3182ce" />
          <MetricsCard label="Precision" value={r.precision.toFixed(4)} />
          <MetricsCard label="Recall" value={r.recall.toFixed(4)} />
          <MetricsCard label="F1 Score" value={r.f1.toFixed(4)} />
          <MetricsCard label="Training Size" value={r.train_size} />
          <MetricsCard label="Test Size" value={r.test_size} />
          <MetricsCard label="Duration" value={status.duration.toFixed(2) + 's'} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '12px', fontWeight: '600' }}>Confusion Matrix</h4>
            <ConfusionMatrix matrix={r.confusion_matrix} />
          </div>
          <div style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '12px', fontWeight: '600' }}>Model Info</h4>
            <div style={{ fontSize: '0.875rem' }}>
              <div style={{ marginBottom: '8px' }}><strong>Run ID:</strong> {r.run_id}</div>
              <div style={{ marginBottom: '8px' }}><strong>URI:</strong> {r.model_uri}</div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '24px', textAlign: 'right' }}>
           <button 
            onClick={() => setActiveStep(4)}
            style={{ padding: '10px 20px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
          >
            Proceed to Testing
          </button>
        </div>
      </div>
    );
  };

  const renderStep4 = () => (
    <div>
      <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>Batch Testing</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>Input JSON (One object per line or Array)</label>
          <textarea 
            value={testInput} 
            onChange={e => setTestInput(e.target.value)}
            style={{ width: '100%', height: '300px', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e0', fontFamily: 'monospace' }}
          />
          <button 
            onClick={runBatchTest}
            style={{ marginTop: '16px', width: '100%', padding: '10px', backgroundColor: '#805ad5', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
          >
            Run Inference
          </button>
        </div>
        
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#f7fafc', textAlign: 'left' }}>
                <th style={{ padding: '8px', borderBottom: '2px solid #e2e8f0' }}>Risk Level</th>
                <th style={{ padding: '8px', borderBottom: '2px solid #e2e8f0' }}>Prob</th>
                <th style={{ padding: '8px', borderBottom: '2px solid #e2e8f0' }}>Input Summary</th>
              </tr>
            </thead>
            <tbody>
              {testResults.map((res, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '8px' }}>
                    <span style={{ 
                      padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 'bold',
                      backgroundColor: res.risk_level === 'High' ? '#fed7d7' : res.risk_level === 'Medium' ? '#feebc8' : '#c6f6d5',
                      color: res.risk_level === 'High' ? '#c53030' : res.risk_level === 'Medium' ? '#c05621' : '#2f855a'
                    }}>
                      {res.risk_level}
                    </span>
                  </td>
                  <td style={{ padding: '8px' }}>{(res.probability * 100).toFixed(1)}%</td>
                  <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    Credit: {typeof res.input.credit_score === 'number' ? res.input.credit_score : '—'}, Debt: {typeof res.input.total_debt === 'number' ? res.input.total_debt : '—'}
                  </td>
                </tr>
              ))}
              {testResults.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ padding: '16px', textAlign: 'center', color: '#a0aec0' }}>No results yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      <div style={{ marginTop: '24px', textAlign: 'right' }}>
         <button 
          onClick={() => setActiveStep(5)}
          style={{ padding: '10px 20px', backgroundColor: '#3182ce', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
        >
          Proceed to Deployment
        </button>
      </div>
    </div>
  );

  const renderStep5 = () => (
    <div>
      <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>Deployment</h3>
      <div style={{ padding: '24px', backgroundColor: '#ebf8ff', borderRadius: '8px', border: '1px solid #bee3f8', marginBottom: '24px' }}>
        <h4 style={{ color: '#2b6cb0', marginBottom: '8px' }}>Ready to Deploy</h4>
        <p style={{ color: '#4a5568', marginBottom: '16px' }}>
          You are about to deploy the model trained in <strong>Run ID: {status?.result?.run_id}</strong> to production.
          This will replace the currently active model.
        </p>
        <div style={{ display: 'flex', gap: '16px' }}>
          <button 
            onClick={deployModel}
            disabled={deployStatus === 'deployed'}
            style={{ 
              padding: '12px 24px', 
              backgroundColor: deployStatus === 'deployed' ? '#48bb78' : '#e53e3e', 
              color: 'white', 
              borderRadius: '6px', 
              border: 'none', 
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '1rem'
            }}
          >
            {deployStatus === 'deployed' ? 'Deployed Successfully' : deployStatus === 'deploying' ? 'Deploying...' : 'Deploy to Production'}
          </button>
        </div>
      </div>
      
      {deployStatus === 'deployed' && (
        <div style={{ padding: '16px', backgroundColor: '#f0fff4', border: '1px solid #c6f6d5', borderRadius: '8px', color: '#2f855a' }}>
          ✓ System updated. New model is now handling live traffic.
        </div>
      )}

      {/* Rollback Section */}
      <div style={{ marginTop: '32px', borderTop: '1px solid #e2e8f0', paddingTop: '24px' }}>
        <h4 style={{ color: '#c53030', marginBottom: '8px', fontWeight: 'bold' }}>Emergency Rollback</h4>
        <p style={{ color: '#4a5568', marginBottom: '16px' }}>
            If the current model is behaving unexpectedly, you can rollback to the previous version immediately.
        </p>
        <button 
            onClick={rollbackModel}
            disabled={rollbackStatus === 'rolling_back' || rollbackStatus === 'rolled_back'}
            style={{ 
                padding: '10px 20px', 
                backgroundColor: '#fff5f5', 
                color: '#c53030', 
                borderRadius: '6px', 
                border: '1px solid #c53030', 
                cursor: 'pointer',
                fontWeight: 'bold',
                opacity: (rollbackStatus === 'rolling_back' || rollbackStatus === 'rolled_back') ? 0.5 : 1
            }}
        >
            {rollbackStatus === 'rolling_back' ? 'Rolling back...' : rollbackStatus === 'rolled_back' ? 'Rolled Back Successfully' : 'Rollback to Previous Version'}
        </button>
        {rollbackMessage && (
            <div style={{ marginTop: '8px', color: rollbackStatus === 'failed' ? '#e53e3e' : '#2f855a', fontSize: '0.875rem' }}>
                {rollbackMessage}
            </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
      <header className="mb-6">
        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">ML Model Training Pipeline</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">End-to-end workflow for training, evaluating, and deploying the Credit Risk Model.</p>
      </header>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          type="button"
          onClick={() => setActiveTab('current')}
          className={`inline-flex items-center rounded-2xl px-3 py-2 text-xs font-semibold border transition-colors ${
            activeTab === 'current'
              ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/70 dark:border-blue-500/20 text-blue-800 dark:text-blue-200'
              : 'bg-white/70 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 hover:bg-white/90 dark:hover:bg-white/[0.06]'
          }`}
        >
          Current Model Metrics
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('train')}
          className={`inline-flex items-center rounded-2xl px-3 py-2 text-xs font-semibold border transition-colors ${
            activeTab === 'train'
              ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/70 dark:border-blue-500/20 text-blue-800 dark:text-blue-200'
              : 'bg-white/70 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 hover:bg-white/90 dark:hover:bg-white/[0.06]'
          }`}
        >
          Training Workflow
        </button>
      </div>

      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
        {activeTab === 'current' && renderCurrentMetrics()}
        
        {activeTab === 'train' && (
            <>
                {/* Progress Stepper */}
                <div style={{ display: 'flex', marginBottom: '40px', borderBottom: '1px solid #e2e8f0', paddingBottom: '20px' }}>
                    {['Configuration', 'Execution', 'Analysis', 'Testing', 'Deployment'].map((label, idx) => {
                    const stepNum = idx + 1;
                    const isActive = activeStep === stepNum;
                    const isCompleted = activeStep > stepNum;
                    return (
                        <div 
                        key={label} 
                        onClick={() => stepNum < activeStep && setActiveStep(stepNum)}
                        style={{ 
                            display: 'flex', alignItems: 'center', marginRight: '40px', cursor: stepNum < activeStep ? 'pointer' : 'default',
                            opacity: activeStep < stepNum ? 0.5 : 1
                        }}
                        >
                        <div style={{ 
                            width: '32px', height: '32px', borderRadius: '50%', 
                            backgroundColor: isActive || isCompleted ? '#3182ce' : '#cbd5e0', 
                            color: 'white', fontWeight: 'bold',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '12px'
                        }}>
                            {isCompleted ? '✓' : stepNum}
                        </div>
                        <span style={{ fontWeight: isActive ? '700' : '500', color: isActive ? '#2d3748' : '#718096' }}>{label}</span>
                        </div>
                    );
                    })}
                </div>

                {activeStep === 1 && renderStep1()}
                {activeStep === 2 && renderStep2()}
                {activeStep === 3 && renderStep3()}
                {activeStep === 4 && renderStep4()}
                {activeStep === 5 && renderStep5()}
            </>
        )}
      </div>
    </div>
  );
};
