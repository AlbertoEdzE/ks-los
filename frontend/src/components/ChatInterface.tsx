import React, { useState, useRef, useEffect } from 'react';
import { sendMessage } from '../api/agent';
import type { ChatMessage } from '../api/agent';
import type { ApplicantCreditProfile } from '../types';

interface Props {
  onProfileReceived: (profile: ApplicantCreditProfile) => void;
}

export const ChatInterface: React.FC<Props> = ({ onProfileReceived }) => {
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I am your Journey Coach. I can help you generate a credit profile and assess loan eligibility. What is your age and territory?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);
  const [suggestionsEnabled, setSuggestionsEnabled] = useState(true);
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('http://localhost:8000/admin/config/suggestions_enabled');
        if (r.ok) {
          const data = await r.json();
          setSuggestionsEnabled(!!data.value);
        }
      } catch {}
    })();
  }, []);
  useEffect(() => {
    const prefix = (surname.trim().length > 0 ? (name + ' ' + surname) : name).trim();
    if (!prefix) {
      setSuggestions([]);
      return;
    }
    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      try {
        const r = await fetch(`http://localhost:8000/chat/suggestions?prefix=${encodeURIComponent(prefix)}&limit=8`, { signal: controller.signal });
        if (r.ok) {
          const data = await r.json();
          setSuggestions(data.items || []);
        }
      } catch {}
    }, 200);
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [name, surname]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const fullName = `${name} ${surname}`.trim();
    if (!fullName) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Please provide your name and surname before chatting.' }]);
      return;
    }
    try {
      const r = await fetch('http://localhost:8000/chat/identity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, surname })
      });
      if (r.ok) {
        const data = await r.json();
        const es = new EventSource(`http://localhost:8000/chat/progress/stream?full_name=${encodeURIComponent(data.full_name)}`);
        es.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data);
            setProgress(payload.progress || 0);
            setCurrentStep(payload.step || '');
          } catch {}
        };
        es.onerror = () => {
          es.close();
        };
      }
    } catch {}

    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage(input, messages);
      
      const assistantMsg: ChatMessage = { 
        role: 'assistant', 
        content: response.response 
      };
      
      setMessages(prev => [...prev, assistantMsg]);

      if (response.credit_profile) {
        onProfileReceived(response.credit_profile);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please ensure the backend is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container" style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '500px', 
      border: '1px solid #ccc', 
      borderRadius: '8px',
      backgroundColor: '#fff'
    }}>
      <div style={{ padding: '12px', borderBottom: '1px solid #eee', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div>
          <label htmlFor="chat-name" style={{ display: 'block', fontSize: '12px', color: '#666' }}>Name</label>
          <input id="chat-name" value={name} onChange={(e) => setName(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
        </div>
        <div>
          <label htmlFor="chat-surname" style={{ display: 'block', fontSize: '12px', color: '#666' }}>Surname</label>
          <input id="chat-surname" value={surname} onChange={(e) => setSurname(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
        </div>
        {suggestionsEnabled && suggestions.length > 0 && (
          <div style={{ gridColumn: '1 / span 2', marginTop: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px' }}>Suggestions</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
              {suggestions.map((s) => (
                <button key={s} onClick={() => {
                  const parts = s.split(' ');
                  setName(parts[0] || '');
                  setSurname(parts.slice(1).join(' ') || '');
                }} style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f8f8f8' }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="messages" style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        <div style={{ marginBottom: '10px' }}>
          <div style={{ height: '12px', backgroundColor: '#eee', borderRadius: '6px', overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, backgroundColor: '#0056b3', height: '100%' }} />
          </div>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
            {currentStep ? `Step: ${currentStep} (${progress}%)` : 'No progress yet'}
          </div>
        </div>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '80%',
            backgroundColor: msg.role === 'user' ? '#0056b3' : '#f0f0f0',
            color: msg.role === 'user' ? '#fff' : '#333',
            padding: '10px 15px',
            borderRadius: '12px',
            whiteSpace: 'pre-wrap'
          }}>
            {msg.content}
          </div>
        ))}
        {loading && <div style={{ alignSelf: 'flex-start', color: '#999', fontStyle: 'italic' }}>Thinking...</div>}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-area" style={{ 
        padding: '15px', 
        borderTop: '1px solid #eee',
        display: 'flex',
        gap: '10px'
      }}>
        <input 
          type="text" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={loading}
          style={{ 
            flex: 1, 
            padding: '10px', 
            borderRadius: '4px', 
            border: '1px solid #ccc' 
          }}
        />
        <button 
          onClick={handleSend} 
          disabled={loading || !input.trim()}
          style={{ 
            padding: '10px 20px', 
            backgroundColor: '#0056b3', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
};
