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
  onFocus?: () => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

function ChatInput({ 
  onSendMessage,
  onFocus,
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
    <div className="border-t border-slate-600 bg-slate-800 p-4 shadow-lg">
      {/* Options panel */}
      {showOptions && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mb-4 p-4 bg-slate-700 rounded-lg border border-slate-600 shadow-sm"
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
                <span className="text-sm font-medium text-gray-200">Use Tools</span>
              </label>
              <div className="text-xs text-gray-400">
                Enable calculator, search, etc.
              </div>
            </div>

            {/* Max Context Tokens */}
            <div className="flex items-center space-x-3">
              <label className="text-sm font-medium text-gray-200 min-w-0">
                Max Context:
              </label>
              <select
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="px-3 py-1 text-sm border border-slate-500 bg-slate-600 text-slate-100 rounded-md focus:ring-primary-400 focus:border-primary-400 transition-colors"
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
          className="flex-shrink-0 p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700"
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
            onFocus={() => onFocus?.()}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={`
              w-full px-4 py-3 pr-12 text-sm border rounded-2xl text-white shadow-sm
              resize-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200
              ${disabled 
                ? 'bg-slate-700 border-slate-600 cursor-not-allowed text-gray-400' 
                : 'bg-slate-800 border-slate-600 hover:border-slate-500 focus:bg-slate-700'
              }
              max-h-32 overflow-y-auto scrollbar-thin placeholder-slate-400
            `}
            style={{ minHeight: '48px' }}
          />
          
          {/* Character count */}
          {message.length > 500 && (
            <div className="absolute bottom-1 right-12 text-xs text-slate-400">
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
                ? 'text-primary-400 bg-primary-900/50' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }
            `}
            title="Message options"
          >
            <Cog6ToothIcon className="w-5 h-5" />
          </button>

          {/* Voice input (placeholder) */}
          <button
            type="button"
            className="p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700"
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
              p-2 rounded-lg transition-all duration-200 shadow-sm
              ${canSend
                ? 'text-white bg-primary-500 hover:bg-primary-600 shadow-md hover:shadow-lg ring-1 ring-primary-400/50'
                : 'text-slate-400 bg-slate-600 cursor-not-allowed'
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
      <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          {isLoading && (
            <>
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="w-1 h-1 bg-primary-400 rounded-full"
              />
              <span className="text-slate-300">Agent is thinking...</span>
            </>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="opacity-75">
            Press Enter to send, Shift+Enter for new line
          </span>
          {useTools && (
            <span className="px-2 py-0.5 bg-green-900/30 text-green-400 rounded-full text-xs border border-green-700/50">
              Tools enabled
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatInput;
