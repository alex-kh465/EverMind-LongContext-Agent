/**
 * Message Component
 * Displays individual chat messages with role-based styling and formatting
 */

import { motion } from 'framer-motion';
import { 
  UserIcon, 
  CpuChipIcon,
  WrenchScrewdriverIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import type { ChatMessage, ToolCall } from '../lib/api';

interface MessageProps {
  message: ChatMessage;
  toolCalls?: ToolCall[];
}

function Message({ message, toolCalls = [] }: MessageProps) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false
    });
  };

  const renderContent = () => {
    // Simple markdown-like formatting
    let content = message.content;
    
    // Convert **bold** to bold
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert *italic* to italic
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert `code` to code with proper contrast based on message type
    const codeClass = isUser 
      ? 'bg-primary-700 text-primary-100 px-1 py-0.5 rounded text-sm font-mono border border-primary-500'
      : 'bg-gray-700 text-gray-200 px-1 py-0.5 rounded text-sm font-mono';
    content = content.replace(/`([^`]+)`/g, `<code class="${codeClass}">$1</code>`);
    
    // Convert newlines to breaks
    content = content.replace(/\n/g, '<br>');

    return <div className="message-content break-words" dangerouslySetInnerHTML={{ __html: content }} />;
  };

  const getIcon = () => {
    if (isUser) return UserIcon;
    if (isTool) return WrenchScrewdriverIcon;
    return CpuChipIcon;
  };

  const IconComponent = getIcon();

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} w-full`}>
      <div className={`
        flex ${isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'} space-x-3 
        max-w-[85%] sm:max-w-[75%] lg:max-w-[65%]
      `}>
        {/* Avatar */}
        <div className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? 'bg-primary-500' : isTool ? 'bg-orange-500' : 'bg-secondary-500'}
        `}>
          <IconComponent className="w-4 h-4 text-white" />
        </div>

        {/* Message content */}
        <div className={`
          flex-1 min-w-0
          ${isUser ? 'text-right' : 'text-left'}
        `}>
          {/* Role and timestamp */}
          <div className={`
            flex items-center space-x-2 mb-1
            ${isUser ? 'justify-end' : 'justify-start'}
          `}>
            <span className="text-xs font-medium text-gray-300 capitalize">
              {message.role}
            </span>
            <ClockIcon className="w-3 h-3 text-gray-500" />
            <span className="text-xs text-gray-500">
              {formatTimestamp(message.timestamp)}
            </span>
            {message.metadata?.optimistic && (
              <span className="text-xs text-yellow-500">Sending...</span>
            )}
          </div>

          {/* Message bubble */}
          <div className={`
            inline-block px-4 py-3 rounded-2xl max-w-full
            ${isUser 
              ? 'bg-primary-600 text-white rounded-br-md shadow-md' 
              : isTool
              ? 'bg-orange-900/20 border border-orange-700 text-orange-200 rounded-bl-md'
              : 'bg-gray-800 border border-gray-600 text-gray-100 rounded-bl-md shadow-sm'
            }
          `}>
            {renderContent()}

            {/* Metadata */}
            {(message.metadata?.model || message.metadata?.tokens_used) && (
              <div className="mt-2 text-xs opacity-70 border-t border-gray-600 pt-2">
                {message.metadata.model && (
                  <span>Model: {message.metadata.model}</span>
                )}
                {message.metadata.tokens_used && (
                  <span className="ml-3">Tokens: {message.metadata.tokens_used}</span>
                )}
              </div>
            )}
          </div>

          {/* Tool calls */}
          {toolCalls.length > 0 && (
            <div className="mt-3 space-y-2">
              {toolCalls.map((toolCall) => (
                <motion.div
                  key={toolCall.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-blue-900/20 border border-blue-700 rounded-lg p-3"
                >
                  <div className="flex items-center space-x-2 mb-2">
                    <WrenchScrewdriverIcon className="w-4 h-4 text-blue-400" />
                    <span className="text-sm font-medium text-blue-200 capitalize">
                      {toolCall.tool_type.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-blue-300">
                      {toolCall.execution_time_ms.toFixed(1)}ms
                    </span>
                  </div>
                  
                  {/* Tool parameters */}
                  <div className="text-xs text-blue-300 mb-2">
                    <strong>Input:</strong> {JSON.stringify(toolCall.parameters)}
                  </div>
                  
                  {/* Tool result */}
                  <div className="text-sm text-blue-100 bg-blue-900/30 rounded p-2 font-mono">
                    {typeof toolCall.result === 'string' 
                      ? toolCall.result 
                      : JSON.stringify(toolCall.result, null, 2)
                    }
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Message;
