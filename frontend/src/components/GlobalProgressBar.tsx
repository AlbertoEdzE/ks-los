import React, { useEffect, useState } from 'react';

interface Props {
  fullName: string;
  onComplete?: () => void;
}

const PROCESS_STEPS = [
  { id: 'intake', label: 'Intake', description: 'Gathering initial applicant information and consent.' },
  { id: 'database_lookup', label: 'Lookup', description: 'Querying external databases (e.g., CreditInfo, CCBL) for credit records.' },
  { id: 'feature_assembly', label: 'Assembly', description: 'Aggregating and normalizing data into a unified feature set.' },
  { id: 'classification', label: 'Classify', description: 'Analyzing patterns and segmenting the applicant profile.' },
  { id: 'model_inference', label: 'Inference', description: 'Running AI models to calculate credit scores and risk probabilities.' },
  { id: 'aggregation', label: 'Decision', description: 'Synthesizing all insights into a final credit decision recommendation.' }
];

const Tooltip = ({ text }: { text: string }) => {
  const [show, setShow] = useState(false);
  return (
    <div 
      style={{ position: 'relative', display: 'inline-block', marginLeft: '4px', cursor: 'help' }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onClick={(e) => { e.stopPropagation(); setShow(!show); }}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
      {show && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#1f2937',
          color: 'white',
          padding: '6px 10px',
          borderRadius: '6px',
          fontSize: '0.7rem',
          whiteSpace: 'nowrap',
          zIndex: 50,
          marginBottom: '6px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}>
          {text}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            borderWidth: '4px',
            borderStyle: 'solid',
            borderColor: '#1f2937 transparent transparent transparent'
          }}></div>
        </div>
      )}
    </div>
  );
};

export const GlobalProgressBar: React.FC<Props> = ({ fullName, onComplete }) => {
  const [currentStepId, setCurrentStepId] = useState<string>('intake');
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set(['intake']));

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
      console.error("EventSource failed");
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
                transition: 'color 0.3s ease',
                display: 'flex',
                alignItems: 'center'
              }}>
                {step.label}
                <Tooltip text={step.description} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

