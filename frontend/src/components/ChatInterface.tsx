import React, { useState, useRef, useEffect } from 'react';
import { sendMessage } from '../api/agent';
import type { ChatMessage } from '../api/agent';
import type { ApplicantCreditProfile } from '../types';

interface Props {
  onProfileReceived: (profile: ApplicantCreditProfile) => void;
}

export const ChatInterface: React.FC<Props> = ({ onProfileReceived }) => {
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

  const handleSend = async () => {
    if (!input.trim() || loading) return;

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
      <div className="messages" style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
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
