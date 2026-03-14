import React, { useState, useEffect } from 'react';

const MetricCard: React.FC<{ label: string; value: string | number | React.ReactNode }> = ({ label, value }) => (
  <div style={{ padding: '16px', backgroundColor: '#f7fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
    <div style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '4px', fontWeight: '500' }}>{label}</div>
    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#2d3748' }}>{value}</div>
  </div>
);

const JsonView: React.FC<{ data: unknown }> = ({ data }) => (
  <pre style={{ 
    backgroundColor: '#f8fafc', 
    padding: '12px', 
    borderRadius: '6px', 
    border: '1px solid #e2e8f0', 
    fontSize: '0.85rem', 
    fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    color: '#4a5568',
    overflowX: 'auto',
    margin: 0
  }}>
    {data ? JSON.stringify(data, null, 2) : 'Loading...'}
  </pre>
);

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
        const r = await fetch('http://localhost:8000/observability/summary');
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Section */}
      <div style={{ padding: '24px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#1a202c', marginBottom: '20px' }}>Model Simulator</h2>
        
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
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '24px' }}>
        {/* Left Column: Score & Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <MetricCard 
            label="Prediction Score" 
            value={score !== null ? (
              <span style={{ color: score > 0.5 ? '#e53e3e' : '#38a169' }}>
                {score.toFixed(4)}
              </span>
            ) : '-'} 
          />
          
          <div style={{ padding: '20px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#2d3748', marginBottom: '12px' }}>Observability Status</h3>
            <JsonView data={summary} />
          </div>
        </div>

        {/* Right Column: Explainability */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ padding: '20px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#2d3748', marginBottom: '12px' }}>Feature Importance (SHAP Proxy)</h3>
            <JsonView data={Object.keys(importances).length ? importances : null} />
          </div>

          <div style={{ padding: '20px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#2d3748', marginBottom: '12px' }}>Input Features</h3>
            <JsonView data={Object.keys(featureValues).length ? featureValues : null} />
          </div>
        </div>
      </div>
    </div>
  );
};
