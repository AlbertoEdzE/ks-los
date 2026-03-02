import React, { useEffect, useState } from 'react';

interface Props {
  fullName: string;
  onComplete?: () => void;
}

interface ProgressState {
  step: string;
  progress: number;
}

export const GlobalProgressBar: React.FC<Props> = ({ fullName, onComplete }) => {
  const [state, setState] = useState<ProgressState>({ step: 'Initializing...', progress: 0 });
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!fullName) return;

    const es = new EventSource(`http://localhost:8000/chat/progress/stream?full_name=${encodeURIComponent(fullName)}`);
    
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        setState({
          step: formatStepName(payload.step),
          progress: payload.progress
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
    <div className="w-full mb-6 p-4 bg-white rounded-lg shadow-sm border border-gray-100" role="status" aria-live="polite">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">{state.step}</span>
        <span className="text-sm font-bold text-indigo-600">{state.progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
        <div 
          className={`h-2.5 rounded-full transition-all duration-500 ease-out ${error ? 'bg-red-500' : 'bg-indigo-600'}`}
          style={{ width: `${state.progress}%` }}
        ></div>
      </div>
    </div>
  );
};

function formatStepName(step: string): string {
  switch (step) {
    case 'database_lookup': return 'Checking Database...';
    case 'feature_assembly': return 'Assembling Profile Features...';
    case 'classification': return 'Running Classification Models...';
    case 'model_inference': return 'Calculating Risk Score...';
    case 'aggregation': return 'Finalizing Assessment...';
    default: return step.replace(/_/g, ' ');
  }
}
