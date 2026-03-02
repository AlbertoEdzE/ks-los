import React, { useEffect, useState } from 'react';

interface Props {
  fullName: string;
  onComplete?: () => void;
}

interface ProgressState {
  step: string;
  progress: number;
}

const PROCESS_STEPS = [
  { id: 'intake', label: 'Intake' },
  { id: 'database_lookup', label: 'Lookup' },
  { id: 'feature_assembly', label: 'Assembly' },
  { id: 'classification', label: 'Classify' },
  { id: 'model_inference', label: 'Inference' },
  { id: 'aggregation', label: 'Decision' }
];

export const GlobalProgressBar: React.FC<Props> = ({ fullName, onComplete }) => {
  const [currentStepId, setCurrentStepId] = useState<string>('intake');
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set(['intake']));
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!fullName) return;

    // Reset state on new name
    setCurrentStepId('intake');
    setCompletedSteps(new Set(['intake']));
    
    const es = new EventSource(`http://localhost:8000/chat/progress/stream?full_name=${encodeURIComponent(fullName)}`);
    
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        const stepId = payload.step;
        
        setCurrentStepId(stepId);
        setCompletedSteps(prev => {
          const newSet = new Set(prev);
          // Mark all previous steps as complete based on order
          const currentIndex = PROCESS_STEPS.findIndex(s => s.id === stepId);
          if (currentIndex !== -1) {
            for (let i = 0; i <= currentIndex; i++) {
              newSet.add(PROCESS_STEPS[i].id);
            }
          }
          return newSet;
        });

        if (payload.progress >= 100) {
          es.close();
          if (onComplete) onComplete();
        }
      } catch (e) {
        console.error("Error parsing progress event", e);
      }
    };

    es.onerror = () => {
      setError(true);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [fullName, onComplete]);

  if (!fullName) return null;

  return (
    <div 
      style={{
        width: '100%',
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: 'white',
        borderRadius: '0.75rem',
        boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        border: '1px solid #f3f4f6',
        boxSizing: 'border-box'
      }}
      role="status" 
      aria-live="polite"
    >
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        {/* Background Line */}
        <div style={{
          position: 'absolute',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: '100%',
          height: '4px',
          backgroundColor: '#e5e7eb',
          zIndex: 0
        }}></div>
        
        {/* Steps */}
        {PROCESS_STEPS.map((step, index) => {
          const isCompleted = completedSteps.has(step.id);
          const isActive = currentStepId === step.id;
          
          return (
            <div key={step.id} style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div 
                style={{
                  width: '2rem',
                  height: '2rem',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: isActive || isCompleted ? '2px solid #4f46e5' : '2px solid #d1d5db',
                  backgroundColor: isActive || isCompleted ? '#4f46e5' : 'white',
                  transform: isActive ? 'scale(1.1)' : 'scale(1)',
                  boxShadow: isActive ? '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)' : 'none',
                  transition: 'all 0.3s ease'
                }}
              >
                {isCompleted ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#6b7280' }}>{index + 1}</span>
                )}
              </div>
              <div style={{
                marginTop: '0.5rem',
                fontSize: '0.75rem',
                fontWeight: 500,
                color: isActive || isCompleted ? '#4338ca' : '#6b7280',
                transition: 'color 0.3s ease'
              }}>
                {step.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

