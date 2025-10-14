/**
 * Chat Page Component
 * Main chat interface with session management and message handling
 */

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  SparklesIcon,
  BoltIcon,
  CircleStackIcon,
} from '@heroicons/react/24/outline';

import Message from '../components/Message';
import ChatInput from '../components/ChatInput';
import SessionSidebar from '../components/SessionSidebar';
import { useSendMessage, useApiError, usePrefetch } from '../hooks/useApi';
import type { ChatResponse } from '../lib/api';

function ChatPage() {
  const { sessionId } = useParams();
  const [messages, setMessages] = useState<ChatResponse[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(sessionId || null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const sendMessageMutation = useSendMessage();
  const { handleError } = useApiError();
  const { prefetchSessions } = usePrefetch();

  // Prefetch sessions on mount
  useEffect(() => {
    prefetchSessions();
  }, [prefetchSessions]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Update current session ID when route changes
  useEffect(() => {
    if (sessionId !== currentSessionId) {
      setCurrentSessionId(sessionId || null);
      setMessages([]); // Clear messages when switching sessions
    }
  }, [sessionId, currentSessionId]);

  const handleSendMessage = async (message: string, options?: any) => {
    try {
      // Add optimistic user message
      const userMessage: ChatResponse = {
        message: {
          id: `temp-${Date.now()}`,
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
          metadata: { optimistic: true }
        },
        session_id: currentSessionId || '',
        retrieved_memories: [],
        tool_calls: [],
        metrics: {}
      };

      setMessages(prev => [...prev, userMessage]);

      // Send message to API
      const response = await sendMessageMutation.mutateAsync({
        message,
        session_id: currentSessionId || undefined,
        use_tools: options?.use_tools ?? true,
        max_context_tokens: options?.max_context_tokens ?? 4000,
      });

      // Remove optimistic message and add real messages
      setMessages(prev => {
        const filtered = prev.filter(msg => !msg.message.metadata?.optimistic);
        // Add user message without optimistic flag and the AI response
        const cleanUserMessage = {
          ...userMessage,
          message: {
            ...userMessage.message,
            metadata: {}
          }
        };
        return [...filtered, cleanUserMessage, response];
      });

      // Update current session ID if this was a new conversation
      if (!currentSessionId && response.session_id) {
        setCurrentSessionId(response.session_id);
        // Update URL without triggering a re-render
        window.history.replaceState(null, '', `/chat/${response.session_id}`);
      }

    } catch (error) {
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => !msg.message.metadata?.optimistic));
      
      const errorMessage = handleError(error);
      alert(`Failed to send message: ${errorMessage}`);
    }
  };

  const isLoading = sendMessageMutation.isPending;

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Session Sidebar */}
      <SessionSidebar />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
                <SparklesIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  {currentSessionId ? 'Conversation' : 'New Chat'}
                </h1>
                <p className="text-sm text-gray-500">
                  {currentSessionId 
                    ? `Session: ${currentSessionId.slice(0, 8)}...`
                    : 'Start a conversation with your AI assistant'
                  }
                </p>
              </div>
            </div>
            
            {/* Session Stats */}
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <CircleStackIcon className="w-4 h-4" />
                <span>{messages.length} messages</span>
              </div>
              {currentSessionId && (
                <div className="flex items-center space-x-1">
                  <BoltIcon className="w-4 h-4" />
                  <span>Tools enabled</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto bg-gray-50 relative">
          {messages.length === 0 ? (
            /* Welcome Screen */
            <div className="h-full flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center max-w-2xl mx-auto px-4"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <SparklesIcon className="w-8 h-8 text-primary-600" />
                </div>
                
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Welcome to LongContext Agent
                </h2>
                
                <p className="text-gray-600 mb-8 leading-relaxed">
                  Your AI assistant with persistent memory and intelligent tools. 
                  Start a conversation and I'll remember our discussion across long interactions.
                </p>

                <div className="grid md:grid-cols-3 gap-6 text-left">
                  <div className="bg-white p-6 rounded-xl border border-gray-200">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                      <CircleStackIcon className="w-5 h-5 text-blue-600" />
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-2">Persistent Memory</h3>
                    <p className="text-sm text-gray-600">
                      I remember our conversations and can reference past discussions
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-xl border border-gray-200">
                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                      <BoltIcon className="w-5 h-5 text-green-600" />
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-2">Smart Tools</h3>
                    <p className="text-sm text-gray-600">
                      Calculator, web search, and Wikipedia integration
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-xl border border-gray-200">
                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                      <SparklesIcon className="w-5 h-5 text-purple-600" />
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-2">Context Aware</h3>
                    <p className="text-sm text-gray-600">
                      Intelligent compression keeps conversations efficient
                    </p>
                  </div>
                </div>

                <div className="mt-8">
                  <p className="text-sm text-gray-500">
                    Try asking me to: calculate something, search for information, or just chat!
                  </p>
                </div>
              </motion.div>
            </div>
          ) : (
            /* Messages List */
            <div className="w-full">
              <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
                {messages.map((response, index) => (
                  <motion.div 
                    key={response.message.id || index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Message
                      message={response.message}
                      toolCalls={response.tool_calls}
                    />
                  </motion.div>
                ))}
              </div>
                
              {/* Loading indicator */}
              {isLoading && (
                <div className="px-4 pb-4">
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-4xl mx-auto"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-secondary-500 rounded-full flex items-center justify-center">
                        <SparklesIcon className="w-4 h-4 text-white" />
                      </div>
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                        <div className="flex space-x-1 items-center">
                          <motion.div
                            animate={{ scale: [1, 1.2, 1] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                            className="w-2 h-2 bg-gray-400 rounded-full"
                          />
                          <motion.div
                            animate={{ scale: [1, 1.2, 1] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                            className="w-2 h-2 bg-gray-400 rounded-full"
                          />
                          <motion.div
                            animate={{ scale: [1, 1.2, 1] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                            className="w-2 h-2 bg-gray-400 rounded-full"
                          />
                          <span className="text-sm text-gray-500 ml-2">AI is thinking...</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          placeholder="Type your message..."
          disabled={false}
        />
      </div>
    </div>
  );
}

export default ChatPage;
