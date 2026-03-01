import { useState } from 'react';
import { generateProfile } from './api/scdg';
import { ApplicantCreditProfile } from './types';
import { CreditProfileView } from './components/CreditProfileView';
import './App.css';

function App() {
  const [profile, setProfile] = useState<ApplicantCreditProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [age, setAge] = useState(30);
  const [territory, setTerritory] = useState('AG');
  const [scenario, setScenario] = useState('');
  const [seed, setSeed] = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateProfile(age, territory, scenario || undefined, seed || undefined);
      setProfile(data);
    } catch (error) {
      console.error('Failed to generate profile:', error);
      alert('Failed to generate profile. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container" style={{ padding: '20px' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>KS LOS - Synthetic Credit Data Generator</h1>
      
      <div className="controls" style={{ 
        maxWidth: '800px', 
        margin: '0 auto 30px', 
        padding: '20px', 
        backgroundColor: '#f0f4f8', 
        borderRadius: '8px',
        display: 'flex',
        gap: '15px',
        flexWrap: 'wrap',
        alignItems: 'flex-end'
      }}>
        <div className="control-group">
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>Age</label>
          <input 
            type="number" 
            value={age} 
            onChange={(e) => setAge(parseInt(e.target.value))} 
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>
        
        <div className="control-group">
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>Territory</label>
          <select 
            value={territory} 
            onChange={(e) => setTerritory(e.target.value)}
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '150px' }}
          >
            <option value="AG">Antigua (AG)</option>
            <option value="GD">Grenada (GD)</option>
            <option value="LC">Saint Lucia (LC)</option>
            <option value="VC">Saint Vincent (VC)</option>
            <option value="DM">Dominica (DM)</option>
            <option value="KN">Saint Kitts (KN)</option>
          </select>
        </div>
        
        <div className="control-group">
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>Scenario (Optional)</label>
          <select 
            value={scenario} 
            onChange={(e) => setScenario(e.target.value)}
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '200px' }}
          >
            <option value="">Auto-Detect</option>
            <option value="THIN_FILE_YOUNG">Thin File (Young)</option>
            <option value="PRIME_ESTABLISHED">Prime Established</option>
            <option value="NEAR_PRIME">Near Prime</option>
            <option value="STRESSED">Stressed</option>
            <option value="DEFAULTED">Defaulted</option>
          </select>
        </div>

        <div className="control-group">
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>Seed (Optional)</label>
          <input 
            type="text" 
            value={seed} 
            onChange={(e) => setSeed(e.target.value)} 
            placeholder="Deterministic Seed"
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
        </div>

        <button 
          onClick={handleGenerate} 
          disabled={loading}
          style={{ 
            padding: '10px 20px', 
            backgroundColor: '#0056b3', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1
          }}
        >
          {loading ? 'Generating...' : 'Generate Profile'}
        </button>
      </div>

      {profile && <CreditProfileView profile={profile} />}
    </div>
  );
}

export default App;
