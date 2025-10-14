/**
 * System Reset Button Component
 * Provides a dangerous action to reset the entire system and clear all data
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrashIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useSystemReset } from '../hooks/useApi';

interface SystemResetButtonProps {
  className?: string;
  onResetComplete?: () => void;
}

export default function SystemResetButton({ className = '', onResetComplete }: SystemResetButtonProps) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const resetMutation = useSystemReset();

  const handleResetClick = () => {
    setShowConfirmDialog(true);
    setConfirmText('');
  };

  const handleConfirmReset = async () => {
    if (confirmText !== 'DELETE ALL DATA') {
      return;
    }

    try {
      await resetMutation.mutateAsync();
      setShowConfirmDialog(false);
      setConfirmText('');
      onResetComplete?.();
    } catch (error) {
      console.error('Reset failed:', error);
    }
  };

  const handleCancel = () => {
    setShowConfirmDialog(false);
    setConfirmText('');
    resetMutation.reset();
  };

  const isConfirmValid = confirmText === 'DELETE ALL DATA';

  return (
    <>
      {/* Reset Button */}
      <button
        onClick={handleResetClick}
        disabled={resetMutation.isPending}
        className={`
          inline-flex items-center px-3 py-2 text-sm font-medium text-red-300 
          bg-red-900/20 border border-red-700 rounded-lg hover:bg-red-900/30 
          focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed transition-colors
          ${className}
        `}
        title="Reset entire system (WARNING: Deletes all data)"
      >
        {resetMutation.isPending ? (
          <>
            <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
            Resetting...
          </>
        ) : (
          <>
            <TrashIcon className="w-4 h-4 mr-2" />
            Reset System
          </>
        )}
      </button>

      {/* Confirmation Dialog */}
      <AnimatePresence>
        {showConfirmDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6"
            >
              {/* Header */}
              <div className="flex items-center mb-4">
                <ExclamationTriangleIcon className="w-8 h-8 text-red-500 mr-3" />
                <h2 className="text-xl font-bold text-white">
                  Confirm System Reset
                </h2>
              </div>

              {/* Warning Content */}
              <div className="mb-6">
                <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-4">
                  <h3 className="text-sm font-semibold text-red-300 mb-2">
                    ⚠️ THIS ACTION CANNOT BE UNDONE
                  </h3>
                  <p className="text-sm text-red-300">
                    This will permanently delete:
                  </p>
                  <ul className="text-sm text-red-300 mt-2 ml-4 space-y-1">
                    <li>• All conversation sessions</li>
                    <li>• All messages and chat history</li>
                    <li>• All stored memories</li>
                    <li>• All performance metrics</li>
                    <li>• All tool execution history</li>
                    <li>• Vector database embeddings</li>
                  </ul>
                </div>

                <p className="text-sm text-gray-300 mb-4">
                  To confirm this action, type <strong>DELETE ALL DATA</strong> in the box below:
                </p>

                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Type: DELETE ALL DATA"
                  className="w-full px-3 py-2 border border-gray-500 bg-gray-700 text-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 placeholder-gray-400"
                  disabled={resetMutation.isPending}
                />
              </div>

              {/* Status Messages */}
              {resetMutation.isError && (
                <div className="mb-4 p-3 bg-red-900/20 border border-red-700 rounded-lg">
                  <div className="flex items-center">
                    <XCircleIcon className="w-5 h-5 text-red-400 mr-2" />
                    <span className="text-sm text-red-300">
                      Reset failed. Please try again or check the server logs.
                    </span>
                  </div>
                </div>
              )}

              {resetMutation.isSuccess && (
                <div className="mb-4 p-3 bg-green-900/20 border border-green-700 rounded-lg">
                  <div className="flex items-center">
                    <CheckCircleIcon className="w-5 h-5 text-green-400 mr-2" />
                    <span className="text-sm text-green-300">
                      System reset completed successfully!
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-3">
                <button
                  onClick={handleCancel}
                  disabled={resetMutation.isPending}
                  className="flex-1 px-4 py-2 text-sm font-medium text-gray-200 bg-gray-700 border border-gray-600 rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmReset}
                  disabled={!isConfirmValid || resetMutation.isPending}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {resetMutation.isPending ? (
                    <>
                      <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin inline" />
                      Resetting...
                    </>
                  ) : (
                    'Reset System'
                  )}
                </button>
              </div>

              {/* Additional Info */}
              <div className="mt-4 p-3 bg-gray-700 rounded-lg">
                <p className="text-xs text-gray-300">
                  💡 <strong>Tip:</strong> After reset, the system will start fresh with no previous data. 
                  You can immediately start new conversations.
                </p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}