import React, { useState, useRef, useEffect } from 'react';
import './AiInterface.css';

const AiInterface = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'system',
      content: '🌌 Kairos AI Assistant ready! Ask me anything about context engineering, development, or system analysis.',
      timestamp: new Date().toISOString()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('auto');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchAvailableModels();
  }, []);

  const fetchAvailableModels = async () => {
    try {
      const response = await fetch('/ai/models');
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data.ollama_models || []);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMessage.content })
      });

      if (response.ok) {
        const data = await response.json();
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date().toISOString(),
          model: data.model_config?.model,
          duration: data.duration
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error('AI request failed');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 1,
        type: 'system',
        content: '🌌 Chat cleared. Kairos AI Assistant ready for new conversation!',
        timestamp: new Date().toISOString()
      }
    ]);
  };

  return (
    <div className="ai-interface">
      <div className="ai-header">
        <div className="header-left">
          <h2>🤖 Kairos AI Assistant</h2>
          <span className="model-info">
            {selectedModel === 'auto' ? 'Auto-Select Model' : selectedModel}
          </span>
        </div>
        <div className="header-controls">
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="model-selector"
          >
            <option value="auto">Auto-Select Best Model</option>
            {availableModels.slice(0, 5).map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
          <button onClick={clearChat} className="clear-btn">
            Clear Chat
          </button>
        </div>
      </div>

      <div className="chat-container">
        <div className="messages-area">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-content">
                <div className="message-text">{message.content}</div>
                <div className="message-meta">
                  <span className="timestamp">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                  {message.model && (
                    <span className="model-used">via {message.model}</span>
                  )}
                  {message.duration && (
                    <span className="duration">{message.duration.toFixed(1)}s</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message ai loading">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div className="message-meta">
                  <span className="timestamp">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className="input-area">
          <div className="input-container">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask Kairos anything about your development workflow..."
              disabled={isLoading}
              className="message-input"
            />
            <button 
              type="submit" 
              disabled={!inputValue.trim() || isLoading}
              className="send-btn"
            >
              {isLoading ? '⏳' : '🚀'}
            </button>
          </div>
          <div className="input-suggestions">
            <button 
              type="button" 
              onClick={() => setInputValue('Analyze the current project structure')}
              className="suggestion-btn"
            >
              📊 Analyze Project
            </button>
            <button 
              type="button" 
              onClick={() => setInputValue('What are the best practices for context engineering?')}
              className="suggestion-btn"
            >
              🧠 Context Tips
            </button>
            <button 
              type="button" 
              onClick={() => setInputValue('Show me system performance metrics')}
              className="suggestion-btn"
            >
              📈 Performance
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AiInterface;
