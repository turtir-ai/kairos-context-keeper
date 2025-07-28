import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import useWebSocket from '../hooks/useWebSocket';

const WebSocketContext = createContext();

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [subscribers, setSubscribers] = useState({});
  const subscribersRef = useRef({});
  
  const {
    socket,
    lastMessage,
    readyState,
    connectionStatus,
    sendMessage,
    sendJsonMessage,
    isConnecting,
    isOpen,
    isClosing,
    isClosed,
    connect,
    disconnect
  } = useWebSocket('ws://localhost:8000/ws', {
    reconnectAttempts: 10,
    reconnectInterval: 2000,
    onMessage: (data) => {
      console.log('📡 WebSocket message received:', data);
      
      // Route message to appropriate subscribers based on message_type or type
      const messageType = data?.message_type || data?.type;
      if (messageType) {
        const messageSubscribers = subscribersRef.current[messageType] || [];
        messageSubscribers.forEach(callback => {
          try {
            callback(data.data || data);
          } catch (error) {
            console.error('❌ Error in message callback:', error);
          }
        });
      }
    },
    onOpen: () => {
      console.log('🟢 WebSocket connection established');
    },
    onClose: (event) => {
      console.log('🔴 WebSocket connection closed:', event);
    },
    onError: (error) => {
      console.error('❌ WebSocket error:', error);
    }
  });

  // Subscribe to message types
  const subscribe = useCallback((messageType, callback) => {
    console.log(`🔔 Subscribing to: ${messageType}`);
    
    setSubscribers(prev => ({
      ...prev,
      [messageType]: [...(prev[messageType] || []), callback]
    }));

    subscribersRef.current = {
      ...subscribersRef.current,
      [messageType]: [...(subscribersRef.current[messageType] || []), callback]
    };

    // Send subscription message to backend
    if (isOpen && sendJsonMessage) {
      sendJsonMessage({
        type: 'subscribe',
        message_type: messageType,
        timestamp: new Date().toISOString()
      });
    }

    // Return unsubscribe function
    return () => {
      console.log(`🔕 Unsubscribing from: ${messageType}`);
      
      setSubscribers(prev => ({
        ...prev,
        [messageType]: (prev[messageType] || []).filter(cb => cb !== callback)
      }));

      subscribersRef.current = {
        ...subscribersRef.current,
        [messageType]: (subscribersRef.current[messageType] || []).filter(cb => cb !== callback)
      };

      // Send unsubscription message to backend
      if (isOpen && sendJsonMessage) {
        sendJsonMessage({
          type: 'unsubscribe',
          message_type: messageType,
          timestamp: new Date().toISOString()
        });
      }
    };
  }, [isOpen, sendJsonMessage]);

  // Send existing subscriptions when connection opens
  useEffect(() => {
    if (isOpen && Object.keys(subscribersRef.current).length > 0) {
      console.log('🔄 Resubscribing to message types after connection...');
      Object.keys(subscribersRef.current).forEach(messageType => {
        if (subscribersRef.current[messageType].length > 0) {
          sendJsonMessage({
            type: 'subscribe',
            message_type: messageType,
            timestamp: new Date().toISOString()
          });
        }
      });
    }
  }, [isOpen, sendJsonMessage]);

  const value = {
    socket,
    lastMessage,
    readyState,
    connectionStatus,
    sendMessage,
    sendJsonMessage,
    subscribe,
    isConnecting,
    isOpen,
    isClosing,
    isClosed,
    isConnected: isOpen,
    connect,
    disconnect,
    subscriberCount: Object.keys(subscribers).length
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketContext;
