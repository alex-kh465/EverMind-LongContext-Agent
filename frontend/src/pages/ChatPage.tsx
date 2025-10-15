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
import { useSendMessage, useApiError, usePrefetch, useCreateSession, useChat, useUpdateSession } from '../hooks/useApi';
import type { ChatResponse } from '../lib/api';
import { apiClient } from '../lib/api';
import { useNavigate } from 'react-router-dom';

function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatResponse[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(sessionId || null);
  const [isCreatingDefaultSession, setIsCreatingDefaultSession] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const sendMessageMutation = useSendMessage();
  const createSessionMutation = useCreateSession();
  const updateSessionMutation = useUpdateSession();
  const { handleError } = useApiError();
  const { prefetchSessions } = usePrefetch();
  
  // Fetch chat data for current session
  const { data: sessionData, isLoading: sessionLoading } = useChat(currentSessionId || undefined);

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

  // Load chat history when session data is available
  useEffect(() => {
    try {
      if (sessionData && sessionData.messages && Array.isArray(sessionData.messages) && sessionData.messages.length > 0) {
        // Only load if we don't already have messages or if session changed
        const currentSessionMessages = messages.filter(msg => msg.session_id === sessionData.id);
        if (currentSessionMessages.length === 0) {
          // Convert session messages to ChatResponse format
          const chatResponses: ChatResponse[] = sessionData.messages.map((msg) => ({
            message: msg,
            session_id: sessionData.id,
            retrieved_memories: [], // We don't have historical memory data
            tool_calls: [], // We don't have historical tool call data
            metrics: {}
          }));
          setMessages(chatResponses);
        }
      } else if (sessionData && (!sessionData.messages || sessionData.messages.length === 0)) {
        // Clear messages if session has no messages
        setMessages([]);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
      // Don't crash, just clear messages
      setMessages([]);
    }
  }, [sessionData, currentSessionId]);

  const ensureSessionExists = async (): Promise<string> => {
    if (currentSessionId) {
      return currentSessionId;
    }

    // Create a new session if one doesn't exist
    setIsCreatingDefaultSession(true);
    try {
      const newSession = await createSessionMutation.mutateAsync({
        title: 'New Chat'
      });
      setCurrentSessionId(newSession.id);
      setIsCreatingDefaultSession(false);
      // Navigate to the new session
      navigate(`/chat/${newSession.id}`, { replace: true });
      return newSession.id;
    } catch (error) {
      console.error('Failed to create session:', error);
      setIsCreatingDefaultSession(false);
      throw error;
    }
  };

  // Generate a title based on the first user message
  const generateSessionTitle = (firstMessage: string): string => {
    // Take the first 50 characters and make it a proper title
    const title = firstMessage.trim().substring(0, 50);
    // If it's too long, cut it at word boundary and add ellipsis
    if (firstMessage.length > 50) {
      const lastSpace = title.lastIndexOf(' ');
      if (lastSpace > 20) {
        return title.substring(0, lastSpace) + '...';
      }
      return title + '...';
    }
    return title;
  };

  // Update session title after first message if it's still "New Chat"
  const updateSessionTitleIfNeeded = async (sessionId: string, firstUserMessage: string) => {
    try {
      // Get fresh session data to check current title
      const currentSession = await apiClient.getSession(sessionId);
      
      // Check if current title is still default
      if (!currentSession || currentSession.title === 'New Chat' || !currentSession.title) {
        const newTitle = generateSessionTitle(firstUserMessage);
        console.log('Updating session title to:', newTitle);
        await updateSessionMutation.mutateAsync({
          sessionId,
          updates: { title: newTitle }
        });
        console.log('Session title updated successfully');
      } else {
        console.log('Session already has a title:', currentSession.title);
      }
    } catch (error) {
      console.error('Failed to update session title:', error);
      // Don't throw - title update is not critical
    }
  };

  const handleInputFocus = () => {
    // Create session proactively when user focuses on input (if not already creating/existing)
    if (!currentSessionId && !isCreatingDefaultSession) {
      ensureSessionExists().catch(error => {
        console.error('Failed to create session on focus:', error);
      });
    }
  };

  const handleSendMessage = async (message: string, options?: any) => {
    try {
      // Ensure we have a session before sending the message
      const sessionId = await ensureSessionExists();
      
      // Add optimistic user message
      const userMessage: ChatResponse = {
        message: {
          id: `temp-${Date.now()}`,
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
          metadata: { optimistic: true }
        },
        session_id: sessionId,
        retrieved_memories: [],
        tool_calls: [],
        metrics: {}
      };

      setMessages(prev => [...prev, userMessage]);

      // Send message to API
      const response = await sendMessageMutation.mutateAsync({
        message,
        session_id: sessionId,
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


    } catch (error) {
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => !msg.message.metadata?.optimistic));
      
      const errorMessage = handleError(error);
      alert(`Failed to send message: ${errorMessage}`);
    }
  };

  // Effect to update session title after first message is confirmed in session data
  useEffect(() => {
    // Only attempt title update if we have:
    // 1. A current session ID
    // 2. Session data with a default title
    // 3. At least one user message in the session
    if (
      currentSessionId &&
      sessionData &&
      (sessionData.title === 'New Chat' || !sessionData.title) &&
      sessionData.messages &&
      sessionData.messages.length > 0
    ) {
      // Find the first user message
      const firstUserMessage = sessionData.messages.find(msg => msg.role === 'user');
      if (firstUserMessage && firstUserMessage.content) {
        console.log('Triggering title update for first user message:', firstUserMessage.content);
        updateSessionTitleIfNeeded(currentSessionId, firstUserMessage.content);
      }
    }
  }, [currentSessionId, sessionData?.title, sessionData?.messages]);

  const isLoading = sendMessageMutation.isPending;
  const isLoadingSession = sessionLoading && currentSessionId;

  return (
    <div className="h-screen flex bg-gray-900">
      {/* Session Sidebar */}
      <SessionSidebar />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header */}
        <div className="bg-gray-800 border-b border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
                <SparklesIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">
                  {currentSessionId 
                    ? (sessionData?.title || 'Conversation')
                    : isCreatingDefaultSession 
                      ? 'Setting up chat...'
                      : 'New Chat'
                  }
                </h1>
                <p className="text-sm text-gray-300">
                  {currentSessionId 
                    ? `Session: ${currentSessionId.slice(0, 8)}...`
                    : isCreatingDefaultSession
                      ? 'Preparing your conversation'
                      : 'Start a conversation with your AI assistant'
                  }
                </p>
              </div>
            </div>
            
            {/* Session Stats */}
            <div className="flex items-center space-x-4 text-sm text-gray-400">
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
        <div className="flex-1 overflow-y-auto bg-gray-900 relative">
          {isLoadingSession ? (
            /* Loading Session */
            <div className="h-full flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center"
              >
                <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-spin">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                </div>
                <p className="text-gray-300">Loading conversation...</p>
              </motion.div>
            </div>
          ) : messages.length === 0 ? (
            /* Welcome Screen */
            <div className="h-full flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center max-w-2xl mx-auto px-4"
              >
                <div className="w-16 h-16 bg-primary-900/50 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <SparklesIcon className="w-8 h-8 text-primary-400" />
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-4">
                  Welcome to EverMind Agent
                </h2>
                
                <p className="text-gray-300 mb-8 leading-relaxed">
                  Your AI assistant with persistent memory and intelligent tools. 
                  Start a conversation and I'll remember our discussion across long interactions.
                </p>

                <div className="grid md:grid-cols-3 gap-6 text-left">
                  <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="w-8 h-8 bg-blue-900/50 rounded-lg flex items-center justify-center mb-4">
                      <CircleStackIcon className="w-5 h-5 text-blue-400" />
                    </div>
                    <h3 className="font-semibold text-white mb-2">Persistent Memory</h3>
                    <p className="text-sm text-gray-300">
                      I remember our conversations and can reference past discussions
                    </p>
                  </div>

                  <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="w-8 h-8 bg-green-900/50 rounded-lg flex items-center justify-center mb-4">
                      <BoltIcon className="w-5 h-5 text-green-400" />
                    </div>
                    <h3 className="font-semibold text-white mb-2">Smart Tools</h3>
                    <p className="text-sm text-gray-300">
                      Calculator, web search, and Wikipedia integration
                    </p>
                  </div>

                  <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="w-8 h-8 bg-purple-900/50 rounded-lg flex items-center justify-center mb-4">
                      <SparklesIcon className="w-5 h-5 text-purple-400" />
                    </div>
                    <h3 className="font-semibold text-white mb-2">Context Aware</h3>
                    <p className="text-sm text-gray-300">
                      Intelligent compression keeps conversations efficient
                    </p>
                  </div>
                </div>

                <div className="mt-8">
                  <p className="text-sm text-gray-400">
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
                      <div className="bg-gray-800 border border-gray-600 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
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
                          <span className="text-sm text-gray-300 ml-2">AI is thinking...</span>
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
          onFocus={handleInputFocus}
          isLoading={isLoading || isCreatingDefaultSession}
          placeholder={isCreatingDefaultSession ? "Setting up chat..." : "Type your message..."}
          disabled={isCreatingDefaultSession}
        />
      </div>
    </div>
  );
}

export default ChatPage;
