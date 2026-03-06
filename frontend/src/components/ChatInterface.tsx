import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendMessage } from '../api/agent';
import type { ChatMessage } from '../api/agent';
import type { ApplicantCreditProfile } from '../types';
import { SuggestionStrip } from './SuggestionStrip';
import type { Suggestion } from './SuggestionStrip';

interface Props {
  onProfileReceived: (profile: ApplicantCreditProfile) => void;
  onNameDetected?: (name: string) => void;
  onAnalysisStart?: () => void;
}

export const ChatInterface: React.FC<Props> = ({ onProfileReceived, onNameDetected, onAnalysisStart }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I am your Journey Coach. I can help you generate a credit profile and assess loan eligibility. To get started, please tell me your full name, age, and territory.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [seedSuggestions, setSeedSuggestions] = useState<Suggestion[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Fetch seed suggestions on mount
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const res = await fetch('http://localhost:8000/chat/suggestions');
        if (res.ok) {
          const data = await res.json();
          const items = data.items.map((item: any) => 
            typeof item === 'string' 
              ? { label: item, text: item } 
              : item
          );
          setSeedSuggestions(items);
        }
      } catch (e) {
        console.error("Failed to fetch suggestions", e);
      }
    };
    fetchSuggestions();
  }, []);

  const handleSend = async (text: string = input) => {
    if (!text.trim() || loading) return;

    // Detect Name (Simple heuristic)
    const nameMatch = text.match(/(?:my name is|i am) ([a-z ]+?)(?:,|$|\.|and)/i);
    if (nameMatch && onNameDetected) {
        onNameDetected(nameMatch[1].trim());
    }

    // Detect Analysis Intent (Bank statement provided)
    const analysisKeywords = ['bank statement', 'account', 'transaction', 'csv', 'json', 'data', 'details', 'history'];
    if (analysisKeywords.some(keyword => text.toLowerCase().includes(keyword)) && onAnalysisStart) {
        onAnalysisStart();
    }

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage(text, messages);
      
      const assistantMsg: ChatMessage = { 
        role: 'assistant', 
        content: response.response 
      };
      setMessages(prev => [...prev, assistantMsg]);

      if (response.credit_profile) {
        onProfileReceived(response.credit_profile);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  // Determine current suggestions
  const getCurrentSuggestions = (): { label: string, items: Suggestion[] } => {
    const lastMsg = messages[messages.length - 1];
    
    if (!lastMsg) return { label: '', items: [] };

    const content = lastMsg.content.toLowerCase();

    // Initial State or User just spoke (and waiting for reply - though loading covers this)
    if (messages.length === 1 || content.includes('full name') || content.includes('territory')) {
      return { 
        label: 'Quick Start (Click to Auto-fill)', 
        items: seedSuggestions.length > 0 ? seedSuggestions : [
           { label: 'Start as Katie (Antigua)', text: 'Katie Brady, Antigua and Barbuda, 34 years old' },
           { label: 'Start as John (Grenada)', text: 'John Doe, Grenada, 28 years old' }
        ]
      };
    }

    // Document Phase
    if (content.includes('bank statement') || content.includes('id') || content.includes('document')) {
      return {
        label: 'Use Sample Data (Since no file upload)',
        items: [
          { label: '📄 Paste Sample Bank Statement', text: 'Here is my bank statement summary:\nAccount: 123456789\nBalance: $15,000\nMonthly Deposits: $4,500\nNo missed payments.' },
          { label: '🆔 Paste Sample ID Info', text: 'Here are my ID details:\nName: Katie Brady\nID Number: AB123456\nNationality: Antigua and Barbuda\nDOB: 1990-05-15' }
        ]
      };
    }

    return { label: '', items: [] };
  };

  const { label: suggestionLabel, items: currentSuggestions } = getCurrentSuggestions();

  return (
    <div style={{
      height: '650px',
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      border: '1px solid #e5e7eb'
    }}>
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>
            Chat with Journey Coach
          </h2>
          <p style={{ fontSize: '13px', color: '#6b7280', margin: '4px 0 0 0' }}>AI-powered loan prequalification</p>
        </div>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4b5563" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
             <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
           </svg>
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        backgroundColor: '#f9fafb',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {messages.map((msg, index) => (
          <div key={index} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div 
              data-testid={`chat-message-${msg.role}`}
              className="chat-message-content"
              style={{
              maxWidth: '80%',
              padding: '12px 16px',
              borderRadius: '16px',
              borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
              borderBottomLeftRadius: msg.role === 'user' ? '16px' : '4px',
              backgroundColor: msg.role === 'user' ? '#4f46e5' : 'white',
              color: msg.role === 'user' ? 'white' : '#1f2937',
              boxShadow: msg.role === 'user' ? '0 1px 2px rgba(79, 70, 229, 0.2)' : '0 1px 2px rgba(0, 0, 0, 0.05)',
              border: msg.role === 'user' ? 'none' : '1px solid #e5e7eb',
              fontSize: '14px',
              lineHeight: '1.6',
            }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '16px',
              borderBottomLeftRadius: '4px',
              padding: '12px 16px',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
              display: 'flex',
              gap: '4px',
              alignItems: 'center'
            }}>
              <div className="typing-dot" style={{ width: '6px', height: '6px', backgroundColor: '#9ca3af', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0s' }}></div>
              <div className="typing-dot" style={{ width: '6px', height: '6px', backgroundColor: '#9ca3af', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.16s' }}></div>
              <div className="typing-dot" style={{ width: '6px', height: '6px', backgroundColor: '#9ca3af', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.32s' }}></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{
        padding: '16px 20px',
        backgroundColor: 'white',
        borderTop: '1px solid #e5e7eb'
      }}>
        {!loading && currentSuggestions.length > 0 && (
           <SuggestionStrip 
             suggestions={currentSuggestions} 
             onSelect={handleSend} 
             label={suggestionLabel}
           />
        )}
        
        <div style={{ display: 'flex', gap: '10px', marginTop: currentSuggestions.length > 0 ? '12px' : '0' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type your message..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '24px',
              border: '1px solid #d1d5db',
              outline: 'none',
              fontSize: '14px',
              backgroundColor: '#f9fafb',
              transition: 'border-color 0.2s, box-shadow 0.2s'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#4f46e5';
              e.target.style.boxShadow = '0 0 0 2px rgba(79, 70, 229, 0.1)';
              e.target.style.backgroundColor = 'white';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#d1d5db';
              e.target.style.boxShadow = 'none';
              e.target.style.backgroundColor = '#f9fafb';
            }}
          />
          <button 
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            aria-label="Send"
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              backgroundColor: loading || !input.trim() ? '#e5e7eb' : '#4f46e5',
              color: 'white',
              border: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s, transform 0.1s',
              boxShadow: loading || !input.trim() ? 'none' : '0 2px 4px rgba(79, 70, 229, 0.3)'
            }}
            onMouseEnter={(e) => {
              if (!loading && input.trim()) {
                e.currentTarget.style.backgroundColor = '#4338ca';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && input.trim()) {
                e.currentTarget.style.backgroundColor = '#4f46e5';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
      `}</style>
    </div>
  );
};
