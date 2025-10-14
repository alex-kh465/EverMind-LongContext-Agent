/**
 * Chat Input Component
 * Handles message input with send functionality, typing indicators, and keyboard shortcuts
 */

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  PaperAirplaneIcon,
  MicrophoneIcon,
  PlusIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

interface ChatInputProps {
  onSendMessage: (message: string, options?: any) => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

function ChatInput({ 
  onSendMessage, 
  isLoading = false, 
  placeholder = "Type your message...",
  disabled = false 
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [useTools, setUseTools] = useState(true);
  const [maxTokens, setMaxTokens] = useState(4000);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  // Focus on mount
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!message.trim() || isLoading || disabled) return;

    const options = {
      use_tools: useTools,
      max_context_tokens: maxTokens
    };

    onSendMessage(message.trim(), options);
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  const canSend = message.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* Options panel */}
      {showOptions && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Use Tools Toggle */}
            <div className="flex items-center space-x-3">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTools}
                  onChange={(e) => setUseTools(e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-gray-700">Use Tools</span>
              </label>
              <div className="text-xs text-gray-500">
                Enable calculator, search, etc.
              </div>
            </div>

            {/* Max Context Tokens */}
            <div className="flex items-center space-x-3">
              <label className="text-sm font-medium text-gray-700 min-w-0">
                Max Context:
              </label>
              <select
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              >
                <option value={2000}>2K tokens</option>
                <option value={4000}>4K tokens</option>
                <option value={8000}>8K tokens</option>
                <option value={16000}>16K tokens</option>
              </select>
            </div>
          </div>
        </motion.div>
      )}

      {/* Input area */}
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        {/* Attachment button */}
        <button
          type="button"
          className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 transition-colors"
          title="Attach file (coming soon)"
        >
          <PlusIcon className="w-5 h-5" />
        </button>

        {/* Main input area */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={`
              w-full px-4 py-3 pr-12 text-sm border border-gray-300 rounded-2xl
              resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
              ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}
              max-h-32 overflow-y-auto scrollbar-thin
            `}
            style={{ minHeight: '48px' }}
          />
          
          {/* Character count */}
          {message.length > 500 && (
            <div className="absolute bottom-1 right-12 text-xs text-gray-400">
              {message.length}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center space-x-2">
          {/* Options toggle */}
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className={`
              p-2 rounded-lg transition-colors
              ${showOptions 
                ? 'text-primary-600 bg-primary-50' 
                : 'text-gray-400 hover:text-gray-600'
              }
            `}
            title="Message options"
          >
            <Cog6ToothIcon className="w-5 h-5" />
          </button>

          {/* Voice input (placeholder) */}
          <button
            type="button"
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title="Voice input (coming soon)"
          >
            <MicrophoneIcon className="w-5 h-5" />
          </button>

          {/* Send button */}
          <motion.button
            type="submit"
            disabled={!canSend}
            whileTap={{ scale: 0.95 }}
            className={`
              p-2 rounded-lg transition-all duration-200
              ${canSend
                ? 'text-white bg-primary-500 hover:bg-primary-600 shadow-md hover:shadow-lg'
                : 'text-gray-400 bg-gray-100 cursor-not-allowed'
              }
            `}
            title={canSend ? 'Send message (Enter)' : 'Type a message to send'}
          >
            {isLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
              />
            ) : (
              <PaperAirplaneIcon className="w-5 h-5" />
            )}
          </motion.button>
        </div>
      </form>

      {/* Typing indicator / status */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-2">
          {isLoading && (
            <>
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="w-1 h-1 bg-primary-500 rounded-full"
              />
              <span>Agent is thinking...</span>
            </>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="opacity-75">
            Press Enter to send, Shift+Enter for new line
          </span>
          {useTools && (
            <span className="px-2 py-0.5 bg-green-100 text-green-600 rounded-full text-xs">
              Tools enabled
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatInput;
