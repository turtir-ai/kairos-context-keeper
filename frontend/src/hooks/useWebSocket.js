import { useState, useEffect, useRef, useCallback } from 'react';

const useWebSocket = (url, options = {}) => {
  const {
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onOpen,
    onClose,
    onError,
    onMessage,
    protocols = []
  } = options;

  const [socket, setSocket] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CONNECTING);
  const [connectionStatus, setConnectionStatus] = useState('Connecting');
  
  const reconnectTimeoutId = useRef();
  const reconnectCount = useRef(0);
  const messageQueue = useRef([]);

  // WebSocket ready states mapping
  const readyStateMap = {
    [WebSocket.CONNECTING]: 'Connecting',
    [WebSocket.OPEN]: 'Open',
    [WebSocket.CLOSING]: 'Closing',
    [WebSocket.CLOSED]: 'Closed'
  };

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url, protocols);
      
      ws.onopen = (event) => {
        console.log('WebSocket connected to:', url);
        setReadyState(WebSocket.OPEN);
        setConnectionStatus('Connected');
        reconnectCount.current = 0;
        
        // Send queued messages
        while (messageQueue.current.length > 0) {
          const message = messageQueue.current.shift();
          ws.send(message);
        }
        
        onOpen?.(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected from:', url, event);
        setReadyState(WebSocket.CLOSED);
        setConnectionStatus('Disconnected');
        
        onClose?.(event);
        
        // Attempt reconnection
        if (reconnectCount.current < reconnectAttempts) {
          reconnectCount.current++;
          setConnectionStatus(`Reconnecting (${reconnectCount.current}/${reconnectAttempts})`);
          
          reconnectTimeoutId.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else {
          setConnectionStatus('Failed to reconnect');
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setConnectionStatus('Error');
        onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data, event);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setLastMessage({ error: 'Failed to parse message', raw: event.data });
        }
      };

      setSocket(ws);
      setReadyState(ws.readyState);
      
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setConnectionStatus('Failed to connect');
      setReadyState(WebSocket.CLOSED);
    }
  }, [url, protocols, reconnectAttempts, reconnectInterval, onOpen, onClose, onError, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
    }
    
    if (socket) {
      socket.close();
    }
  }, [socket]);

  const sendMessage = useCallback((message) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      socket.send(messageStr);
      return true;
    } else {
      // Queue message if not connected
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      messageQueue.current.push(messageStr);
      return false;
    }
  }, [socket]);

  const sendJsonMessage = useCallback((object) => {
    return sendMessage(JSON.stringify(object));
  }, [sendMessage]);

  // Subscribe to specific message types
  const subscribe = useCallback((messageType, callback) => {
    const subscription = {
      type: 'subscribe',
      message_type: messageType,
      timestamp: new Date().toISOString()
    };
    
    sendJsonMessage(subscription);
    
    // Return unsubscribe function
    return () => {
      const unsubscription = {
        type: 'unsubscribe',
        message_type: messageType,
        timestamp: new Date().toISOString()
      };
      sendJsonMessage(unsubscription);
    };
  }, [sendJsonMessage]);

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, []); // Remove dependencies to prevent reconnections

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutId.current) {
        clearTimeout(reconnectTimeoutId.current);
      }
    };
  }, []);

  return {
    socket,
    lastMessage,
    readyState,
    connectionStatus,
    sendMessage,
    sendJsonMessage,
    subscribe,
    connect,
    disconnect,
    isConnecting: readyState === WebSocket.CONNECTING,
    isOpen: readyState === WebSocket.OPEN,
    isClosing: readyState === WebSocket.CLOSING,
    isClosed: readyState === WebSocket.CLOSED,
  };
};

export default useWebSocket;
