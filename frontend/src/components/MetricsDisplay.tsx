/**
 * Metrics Display Component
 * Shows real-time system performance metrics including memory, response times, and session stats
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChartBarIcon,
  ClockIcon,
  CpuChipIcon,
  ServerIcon,
  EyeIcon,
  EyeSlashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { usePerformanceMetrics, useSystemHealth } from '../hooks/useApi';

export default function MetricsDisplay() {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const { 
    data: metrics, 
    isLoading: metricsLoading, 
    error: metricsError,
    refetch: refetchMetrics 
  } = usePerformanceMetrics();
  
  const { 
    data: health, 
    isLoading: healthLoading, 
    error: healthError,
    refetch: refetchHealth 
  } = useSystemHealth();

  const handleRefresh = () => {
    refetchMetrics();
    refetchHealth();
  };

  const formatNumber = (num: number, decimals: number = 1): string => {
    return num.toLocaleString(undefined, { 
      minimumFractionDigits: decimals, 
      maximumFractionDigits: decimals 
    });
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getHealthStatus = () => {
    if (healthError || !health) return { color: 'red', icon: ExclamationTriangleIcon, text: 'Offline' };
    if (health.status === 'healthy') return { color: 'green', icon: CheckCircleIcon, text: 'Healthy' };
    return { color: 'yellow', icon: ExclamationTriangleIcon, text: 'Warning' };
  };

  const healthStatus = getHealthStatus();
  const StatusIcon = healthStatus.icon;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* Header */}
      <div className="p-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ChartBarIcon className="w-5 h-5 text-gray-600" />
          <h3 className="text-sm font-medium text-gray-900">System Metrics</h3>
          <div className="flex items-center space-x-1">
            <StatusIcon className={`w-3 h-3 text-${healthStatus.color}-500`} />
            <span className={`text-xs text-${healthStatus.color}-600`}>
              {healthStatus.text}
            </span>
          </div>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={handleRefresh}
            disabled={metricsLoading || healthLoading}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
            title="Refresh metrics"
          >
            <ArrowPathIcon className={`w-4 h-4 ${(metricsLoading || healthLoading) ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-gray-400 hover:text-gray-600"
            title={isExpanded ? "Collapse metrics" : "Expand metrics"}
          >
            {isExpanded ? (
              <EyeSlashIcon className="w-4 h-4" />
            ) : (
              <EyeIcon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Compact View */}
      {!isExpanded && (
        <div className="p-3">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-lg font-bold text-primary-600">
                {health?.active_sessions || 0}
              </div>
              <div className="text-xs text-gray-500">Sessions</div>
            </div>
            <div>
              <div className="text-lg font-bold text-green-600">
                {metrics ? formatNumber(metrics.response_latency_ms) : '--'}ms
              </div>
              <div className="text-xs text-gray-500">Latency</div>
            </div>
            <div>
              <div className="text-lg font-bold text-blue-600">
                {health ? formatBytes(health.memory_usage_mb * 1024 * 1024) : '--'}
              </div>
              <div className="text-xs text-gray-500">Memory</div>
            </div>
          </div>
        </div>
      )}

      {/* Expanded View */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-4">
              {/* Performance Metrics */}
              {metrics && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                    <CpuChipIcon className="w-4 h-4 mr-1" />
                    Performance
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatNumber(metrics.response_latency_ms)}ms
                      </div>
                      <div className="text-xs text-gray-500">Response Latency</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatNumber(metrics.context_retention_accuracy * 100)}%
                      </div>
                      <div className="text-xs text-gray-500">Context Accuracy</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatNumber(metrics.compression_ratio, 2)}x
                      </div>
                      <div className="text-xs text-gray-500">Compression Ratio</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatNumber(metrics.retrieval_precision * 100)}%
                      </div>
                      <div className="text-xs text-gray-500">Retrieval Precision</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Memory & Sessions */}
              {(metrics || health) && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                    <ServerIcon className="w-4 h-4 mr-1" />
                    Memory & Sessions
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {metrics?.total_memories.toLocaleString() || '--'}
                      </div>
                      <div className="text-xs text-gray-500">Total Memories</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {health?.active_sessions || '--'}
                      </div>
                      <div className="text-xs text-gray-500">Active Sessions</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {metrics ? formatNumber(metrics.memory_growth_rate * 100) : '--'}%
                      </div>
                      <div className="text-xs text-gray-500">Memory Growth</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {health ? formatBytes(health.memory_usage_mb * 1024 * 1024) : '--'}
                      </div>
                      <div className="text-xs text-gray-500">System Memory</div>
                    </div>
                  </div>
                </div>
              )}

              {/* System Health */}
              {health && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                    <ClockIcon className="w-4 h-4 mr-1" />
                    System Health
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatUptime(health.uptime_seconds)}
                      </div>
                      <div className="text-xs text-gray-500">Uptime</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className="font-medium text-gray-900">
                        {formatNumber(health.cpu_usage_percent)}%
                      </div>
                      <div className="text-xs text-gray-500">CPU Usage</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className={`font-medium ${health.database_connected ? 'text-green-600' : 'text-red-600'}`}>
                        {health.database_connected ? 'Connected' : 'Disconnected'}
                      </div>
                      <div className="text-xs text-gray-500">Database</div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                      <div className={`font-medium ${health.openai_api_available ? 'text-green-600' : 'text-red-600'}`}>
                        {health.openai_api_available ? 'Available' : 'Unavailable'}
                      </div>
                      <div className="text-xs text-gray-500">OpenAI API</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error States */}
              {(metricsError || healthError) && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <div className="text-sm text-red-800">
                    Failed to load metrics. Check backend connection.
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
