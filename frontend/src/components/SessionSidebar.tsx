/**
 * Session Sidebar Component
 * Displays list of chat sessions with create/delete functionality
 */

import { Link, useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  ChatBubbleLeftIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { useSessions, useDeleteSession, useCreateSession } from '../hooks/useApi';
import MetricsDisplay from './MetricsDisplay';

export default function SessionSidebar() {
  const { sessionId: currentSessionId } = useParams();
  const navigate = useNavigate();
  
  const { data: sessionsData, isLoading } = useSessions();
  const deleteSessionMutation = useDeleteSession();
  const createSessionMutation = useCreateSession();
  
  const sessions = sessionsData?.sessions || [];

  const handleCreateSession = async () => {
    try {
      const newSession = await createSessionMutation.mutateAsync({ 
        title: `Chat ${new Date().toLocaleString()}` 
      });
      // Navigate to new session
      navigate(`/chat/${newSession.id}`);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (window.confirm('Are you sure you want to delete this session?')) {
      try {
        await deleteSessionMutation.mutateAsync(sessionId);
        // If we're currently viewing this session, navigate to home
        if (currentSessionId === sessionId) {
          navigate('/chat');
        }
      } catch (error) {
        console.error('Failed to delete session:', error);
      }
    }
  };

  const formatSessionTitle = (session: any) => {
    if (session.title && session.title !== 'New Session') {
      return session.title;
    }
    return `Chat ${new Date(session.created_at).toLocaleDateString()}`;
  };

  return (
    <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-gray-600 bg-gray-800 flex-shrink-0">
        <button
          onClick={() => {
            console.log('New Chat button clicked!');
            handleCreateSession();
          }}
          disabled={createSessionMutation.isPending}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50 border-2 border-blue-700"
          style={{ minHeight: '44px' }}
        >
          <PlusIcon className="w-5 h-5" />
          <span>New Chat</span>
          {createSessionMutation.isPending && (
            <div className="ml-2 animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
          )}
        </button>
        
        {/* Debug info */}
        <div className="mt-2 text-xs text-gray-400 text-center">
          Sessions: {sessions.length} | Loading: {isLoading ? 'Yes' : 'No'}
        </div>
      </div>

      {/* Main Content Area - Contains sessions and metrics */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <ChatBubbleLeftIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              <AnimatePresence>
                {sessions.map((session: any) => {
                  const isActive = currentSessionId === session.id;
                  return (
                    <motion.div
                      key={session.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className={`group relative`}
                    >
                      <Link
                        to={`/chat/${session.id}`}
                        className={`
                          flex items-center space-x-3 w-full px-3 py-2 rounded-lg text-left transition-colors
                          ${
                            isActive
                              ? 'bg-primary-900/50 text-primary-300 border border-primary-700'
                              : 'text-gray-300 hover:bg-gray-700'
                          }
                        `}
                      >
                        <div className={`w-2 h-2 rounded-full ${
                          isActive ? 'bg-primary-400' : 'bg-gray-500'
                        }`} />
                        
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {formatSessionTitle(session)}
                          </p>
                          <p className="text-xs text-gray-400 truncate">
                            {session.message_count || 0} messages
                          </p>
                        </div>
                        
                        {isActive && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="w-2 h-2 bg-primary-400 rounded-full"
                          />
                        )}
                      </Link>
                      
                      {/* Delete button */}
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          handleDeleteSession(session.id);
                        }}
                        disabled={deleteSessionMutation.isPending}
                        className="absolute right-2 top-1/2 transform -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all"
                      >
                        <TrashIcon className="w-3 h-3" />
                      </button>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>
        
        {/* Footer - Metrics Display */}
        <div className="p-4 border-t border-gray-600 flex-shrink-0">
          <MetricsDisplay />
        </div>
      </div>
    </div>
  );
}
