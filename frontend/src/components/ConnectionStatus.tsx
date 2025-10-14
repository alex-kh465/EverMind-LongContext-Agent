/**
 * Connection Status Component
 * Shows real-time backend connection status
 */

import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  XCircleIcon 
} from '@heroicons/react/20/solid';
import { useConnectionStatus, useSystemHealth } from '../hooks/useApi';

function ConnectionStatus() {
  const { data: isConnected, isLoading: connectionLoading } = useConnectionStatus();
  const { data: health, isError: healthError } = useSystemHealth();

  // Determine overall status - only show critical issues
  const getStatus = () => {
    // Don't show checking state to avoid flash of loading
    if (connectionLoading) return 'healthy';
    if (!isConnected) return 'disconnected';
    // Don't show degraded status to avoid unnecessary popups
    return 'healthy';
  };

  const status = getStatus();

  const statusConfig = {
    checking: {
      color: 'bg-yellow-600',
      icon: ExclamationTriangleIcon,
      text: 'Checking connection...',
      textColor: 'text-yellow-100'
    },
    healthy: {
      color: 'bg-green-600',
      icon: CheckCircleIcon,
      text: 'Connected',
      textColor: 'text-green-100'
    },
    degraded: {
      color: 'bg-yellow-600',
      icon: ExclamationTriangleIcon,
      text: 'Limited functionality',
      textColor: 'text-yellow-100'
    },
    disconnected: {
      color: 'bg-red-600',
      icon: XCircleIcon,
      text: 'Connection lost',
      textColor: 'text-red-100'
    }
  };

  const config = statusConfig[status];
  const IconComponent = config.icon;

  // Only show if not healthy
  if (status === 'healthy') return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        className="fixed top-0 left-0 right-0 z-50"
      >
        <div className={`${config.color} ${config.textColor} px-4 py-2`}>
          <div className="flex items-center justify-center space-x-2 text-sm font-medium">
            <IconComponent className="h-4 w-4" />
            <span>{config.text}</span>
            {health && (
              <span className="text-xs opacity-75">
                • DB: {health.database_connected ? '✓' : '✗'}
                • AI: {health.openai_api_available ? '✓' : '✗'}
              </span>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default ConnectionStatus;
