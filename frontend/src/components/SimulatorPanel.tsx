import React, { useState, useEffect } from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };

const MetricCard: React.FC<{ label: string; value: string | number | React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-3xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
    <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</div>
    <div className="mt-1 text-2xl font-black tracking-tight text-slate-900 dark:text-white">{value}</div>
  </div>
);

function prettyJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

const KeyValueGrid: React.FC<{ data: Record<string, unknown> }> = ({ data }) => {
  const entries = Object.entries(data).slice(0, 16);
  return (
    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
      {entries.map(([k, v]) => (
        <div key={k} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
          <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider break-all">{k}</div>
          <div className="mt-1 text-sm text-slate-800 dark:text-slate-200 break-words">
            {v === null || v === undefined ? '—' : typeof v === 'object' ? (Array.isArray(v) ? `Array(${v.length})` : `Object(${Object.keys(v as any).length})`) : String(v)}
          </div>
        </div>
      ))}
    </div>
  );
};

const BarList: React.FC<{ title: string; data: Record<string, number> }> = ({ title, data }) => {
  const rows = Object.entries(data)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 12);
  const max = rows.reduce((m, [, v]) => Math.max(m, Math.abs(v)), 0) || 1;
  return (
    <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">{title}</h3>
        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">{rows.length} shown</span>
      </div>
      {rows.length === 0 ? (
        <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No data.</div>
      ) : (
        <div className="mt-4 grid gap-2">
          {rows.map(([k, v]) => {
            const w = `${Math.round((Math.abs(v) / max) * 100)}%`;
            const tone = v >= 0 ? 'bg-emerald-500/70' : 'bg-red-500/70';
            return (
              <div key={k} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 break-all">{k}</div>
                  <div className="text-[12px] font-black text-slate-900 dark:text-white">{v.toFixed(4)}</div>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-100 dark:bg-white/[0.06] overflow-hidden">
                  <div className={`h-full ${tone}`} style={{ width: w }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <details className="mt-4">
        <summary className="cursor-pointer text-xs font-semibold text-slate-600 dark:text-slate-300">View raw JSON</summary>
        <pre className="mt-3 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[320px] overflow-auto">
          {prettyJson(data)}
        </pre>
      </details>
    </div>
  );
};

const InputGroup: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div style={{ marginBottom: '16px' }}>
    <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.875rem', fontWeight: '500', color: '#4a5568' }}>{label}</label>
    {children}
  </div>
);

export const SimulatorPanel: React.FC = () => {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [score, setScore] = useState<number | null>(null);
  
  // Feature states
  const [age, setAge] = useState(30);
  const [creditScore, setCreditScore] = useState(720);
  const [utilizationRatio, setUtilizationRatio] = useState(0.3);
  const [totalDebt, setTotalDebt] = useState(5000);
  const [historyLengthMonths, setHistoryLengthMonths] = useState(48);
  const [derogatoryMarks, setDerogatoryMarks] = useState(0);
  const [thinFileFlag, setThinFileFlag] = useState(0);

  // Derived / Other states
  const [territory, setTerritory] = useState('ECCU');
  const [featureValues, setFeatureValues] = useState<Record<string, number>>({});
  const [importances, setImportances] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('http://localhost:8000/observability/summary', { headers: ADMIN_HEADERS });
        if (r.ok) {
          const data = (await r.json()) as Record<string, unknown>;
          setSummary(data);
        }
      } catch (err) {
        console.error('Failed to load observability summary', err);
      }
    })();
  }, []);

  const runSimulation = async () => {
    setLoading(true);
    try {
      // Construct profile object matching backend expectations
      // We are mocking the profile structure needed by explain/inference
      const profile = {
        metadata: {
            source: "synthetic",
            query_timestamp: new Date().toISOString(),
            territory: territory,
            consent_token: "simulated"
        },
        identity: {
            full_name: "Simulated User",
            date_of_birth: new Date(new Date().getFullYear() - age, 0, 1).toISOString().split('T')[0],
            national_id_hash: "sim",
            address: { line1: "Sim", city: "Sim", territory: territory, territory_code: "SIM" }
        },
        summary: {
            credit_score: creditScore,
            score_band: "SIMULATED",
            total_accounts: 5,
            open_accounts: 3,
            closed_accounts: 2,
            total_credit_limit_xcd: 10000,
            total_current_balance_xcd: totalDebt,
            utilization_ratio: utilizationRatio,
            total_past_due_xcd: 0,
            months_oldest_account: historyLengthMonths,
            months_newest_account: 12,
            derogatory_marks: derogatoryMarks,
            thin_file: thinFileFlag === 1,
            thin_file_reason: null
        },
        payment_behavior: {
            on_time_payments_pct: 1.0,
            late_30_days_count: 0,
            late_60_days_count: 0,
            late_90_plus_days_count: 0,
            charge_offs: 0,
            collections: 0,
            worst_payment_status_ever: "C",
            payment_history_24m: "111111111111111111111111"
        },
        trade_lines: [],
        inquiries: [],
        flags: {
            has_bankruptcy: false,
            has_foreclosure: false,
            has_active_collections: false,
            is_deceased: false,
            fraud_alert: false
        }
      };

      const exp = await fetch('http://localhost:8000/explain/inference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile })
      });
      if (exp.ok) {
        const data = await exp.json();
        setScore(typeof data.score === 'number' ? data.score : null);
        setFeatureValues(data.feature_values || {});
        setImportances(data.feature_importances || {});
      }
    } catch (e) {
        console.error("Simulation failed", e);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    fontSize: '0.95rem',
    color: '#2d3748',
    outline: 'none',
    transition: 'border-color 0.2s',
  };

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      {/* Header Section */}
      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Model Simulator</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Run controlled feature perturbations and view model explanations.</p>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
          
          <InputGroup label="Age (Years)">
            <input type="number" value={age} onChange={(e) => setAge(Number(e.target.value))} style={inputStyle} />
          </InputGroup>

          <InputGroup label="Credit Score">
            <input type="number" value={creditScore} onChange={(e) => setCreditScore(Number(e.target.value))} style={inputStyle} />
          </InputGroup>

          <InputGroup label="Utilization Ratio (0-1)">
            <input type="number" step="0.01" value={utilizationRatio} onChange={(e) => setUtilizationRatio(Number(e.target.value))} style={inputStyle} />
          </InputGroup>

          <InputGroup label="Total Debt">
            <input type="number" value={totalDebt} onChange={(e) => setTotalDebt(Number(e.target.value))} style={inputStyle} />
          </InputGroup>

          <InputGroup label="History Length (Months)">
             <input type="number" value={historyLengthMonths} onChange={(e) => setHistoryLengthMonths(Number(e.target.value))} style={inputStyle} />
          </InputGroup>
          
           <InputGroup label="Derogatory Marks">
             <input type="number" value={derogatoryMarks} onChange={(e) => setDerogatoryMarks(Number(e.target.value))} style={inputStyle} />
          </InputGroup>

          <InputGroup label="ci_thin_file_flag">
             <select 
                value={thinFileFlag} 
                onChange={(e) => setThinFileFlag(Number(e.target.value))}
                style={inputStyle}
             >
                <option value={0}>No (0)</option>
                <option value={1}>Yes (1)</option>
             </select>
          </InputGroup>

           <InputGroup label="Territory">
            <select value={territory} onChange={(e) => setTerritory(e.target.value)} style={inputStyle}>
                <option value="ECCU">ECCU</option>
                <option value="JM">Jamaica</option>
                <option value="TT">Trinidad</option>
            </select>
          </InputGroup>
        </div>
        
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
             <button 
                onClick={runSimulation} 
                disabled={loading}
                style={{ 
                padding: '12px 32px', 
                backgroundColor: loading ? '#63b3ed' : '#3182ce', 
                color: 'white', 
                border: 'none', 
                borderRadius: '6px', 
                fontWeight: '600', 
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
            >
                {loading ? 'Simulating...' : 'Run Simulation'}
            </button>
        </div>
      </div>

      {/* Results Section */}
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Left Column: Score & Summary */}
        <div className="flex flex-col gap-6">
          <MetricCard 
            label="Prediction Score" 
            value={score !== null ? (
              <span style={{ color: score > 0.5 ? '#e53e3e' : '#38a169' }}>
                {score.toFixed(4)}
              </span>
            ) : '-'} 
          />
          
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Observability Status</h3>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">local</span>
            </div>
            {summary ? (
              <>
                <KeyValueGrid data={summary} />
                <details className="mt-4">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-600 dark:text-slate-300">View raw JSON</summary>
                  <pre className="mt-3 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[320px] overflow-auto">
                    {prettyJson(summary)}
                  </pre>
                </details>
              </>
            ) : (
              <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No summary available.</div>
            )}
          </div>
        </div>

        {/* Right Column: Explainability */}
        <div className="flex flex-col gap-6">
          <BarList title="Feature importance (SHAP proxy)" data={importances} />
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Input features</h3>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">{Object.keys(featureValues).length} fields</span>
            </div>
            {Object.keys(featureValues).length ? (
              <>
                <KeyValueGrid data={featureValues as Record<string, unknown>} />
                <details className="mt-4">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-600 dark:text-slate-300">View raw JSON</summary>
                  <pre className="mt-3 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[320px] overflow-auto">
                    {prettyJson(featureValues)}
                  </pre>
                </details>
              </>
            ) : (
              <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No features available.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
