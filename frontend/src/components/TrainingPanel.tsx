import React, { useState } from 'react';

export const TrainingPanel: React.FC = () => {
  const [activeStep, setActiveStep] = useState(1);
  const [rationale, setRationale] = useState('Periodic refresh');
  const [plan, setPlan] = useState<any>(null);
  const [trainingStatus, setTrainingStatus] = useState('idle');
  const [trainingResult, setTrainingResult] = useState<any>(null);
  const [driftReportUrl, setDriftReportUrl] = useState('');

  const generatePlan = async () => {
    try {
      const res = await fetch('http://localhost:8000/training/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rationale })
      });
      if (res.ok) {
        const data = await res.json();
        setPlan(data.plan);
        setActiveStep(2);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const executeTraining = async () => {
    if (!plan) return;
    setTrainingStatus('running');
    try {
      const res = await fetch('http://localhost:8000/training/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hyperparameters: plan.hyperparameters,
          n_samples: plan.n_samples,
          notes: rationale
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTrainingResult(data.result);
        setTrainingStatus('completed');
        setActiveStep(3);
      } else {
        setTrainingStatus('failed');
      }
    } catch (e) {
      setTrainingStatus('failed');
      console.error(e);
    }
  };

  const runDrift = async () => {
    try {
      const res = await fetch('http://localhost:8000/training/drift', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setDriftReportUrl(data.report_endpoint); // Using endpoint from response
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '24px', color: '#1a202c' }}>ML Model Training Pipeline</h2>
      
      <div style={{ display: 'flex', marginBottom: '32px', borderBottom: '1px solid #e2e8f0', paddingBottom: '16px' }}>
        {[1, 2, 3].map((step) => (
          <div key={step} style={{ 
            display: 'flex', alignItems: 'center', marginRight: '32px',
            color: activeStep >= step ? '#3b82f6' : '#cbd5e0',
            fontWeight: activeStep >= step ? '600' : '400'
          }}>
            <div style={{ 
              width: '32px', height: '32px', borderRadius: '50%', 
              backgroundColor: activeStep >= step ? '#3b82f6' : '#edf2f7',
              color: activeStep >= step ? '#ffffff' : '#a0aec0',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginRight: '12px', fontSize: '0.9rem'
            }}>
              {step}
            </div>
            {step === 1 ? 'Planning' : step === 2 ? 'Execution' : 'Deployment'}
          </div>
        ))}
      </div>

      {activeStep === 1 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '24px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '16px' }}>Training Plan</h3>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#4a5568' }}>Rationale</label>
            <textarea 
              value={rationale} 
              onChange={(e) => setRationale(e.target.value)}
              style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #cbd5e0', minHeight: '100px' }}
            />
          </div>
          <button 
            onClick={generatePlan}
            style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: '500', cursor: 'pointer' }}
          >
            Generate Plan
          </button>
        </div>
      )}

      {activeStep === 2 && plan && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '24px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '16px' }}>Review & Execute</h3>
          <div style={{ backgroundColor: '#f7fafc', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
            <pre style={{ margin: 0, overflowX: 'auto', fontSize: '0.9rem' }}>{JSON.stringify(plan, null, 2)}</pre>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button 
              onClick={executeTraining}
              disabled={trainingStatus === 'running'}
              style={{ 
                padding: '10px 20px', 
                backgroundColor: trainingStatus === 'running' ? '#cbd5e0' : '#3b82f6', 
                color: '#fff', border: 'none', borderRadius: '6px', fontWeight: '500', cursor: 'pointer', marginRight: '16px'
              }}
            >
              {trainingStatus === 'running' ? 'Training...' : 'Execute Training'}
            </button>
            {trainingStatus === 'failed' && <span style={{ color: '#e53e3e' }}>Training Failed</span>}
          </div>
        </div>
      )}

      {activeStep === 3 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', padding: '24px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '16px' }}>Results & Deployment</h3>
          <div style={{ backgroundColor: '#f0fff4', padding: '16px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #c6f6d5' }}>
            <h4 style={{ color: '#2f855a', margin: '0 0 8px 0' }}>Training Successful</h4>
            <pre style={{ margin: 0, overflowX: 'auto', fontSize: '0.9rem' }}>{JSON.stringify(trainingResult, null, 2)}</pre>
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
             <button 
              onClick={runDrift}
              style={{ padding: '10px 20px', backgroundColor: '#805ad5', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: '500', cursor: 'pointer' }}
            >
              Run Drift Check
            </button>
            {driftReportUrl && (
              <a 
                href={`http://localhost:8000${driftReportUrl}`} 
                target="_blank" 
                rel="noreferrer"
                style={{ padding: '10px 20px', backgroundColor: '#edf2f7', color: '#4a5568', textDecoration: 'none', borderRadius: '6px', fontWeight: '500', display: 'inline-block' }}
              >
                View Report
              </a>
            )}
            <button 
              onClick={() => { setActiveStep(1); setPlan(null); setTrainingResult(null); setTrainingStatus('idle'); }}
              style={{ padding: '10px 20px', backgroundColor: 'transparent', color: '#718096', border: '1px solid #cbd5e0', borderRadius: '6px', fontWeight: '500', cursor: 'pointer' }}
            >
              Start New Cycle
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
