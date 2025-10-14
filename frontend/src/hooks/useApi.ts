/**
 * React Query hooks for LongContext Agent API
 * Provides type-safe, cached API operations with loading and error states
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import type {
  ChatRequest,
  ChatResponse,
  MemoryQuery
} from '../lib/api';

// Query keys for consistent cache management
export const queryKeys = {
  health: ['health'],
  metrics: ['metrics'],
  config: ['config'],
  sessions: ['sessions'],
  memories: (query: string) => ['memories', query],
  chat: (sessionId?: string) => ['chat', sessionId],
} as const;

// Chat hooks
export function useSendMessage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (request: ChatRequest) => apiClient.sendMessage(request),
    onSuccess: (data: ChatResponse) => {
      // Invalidate sessions to refresh the list
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
      
      // Invalidate the specific chat to trigger fresh data fetch
      // This is more reliable than trying to update cache manually
      if (data.session_id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.chat(data.session_id) });
      }
    },
    onError: (error) => {
      console.error('❌ Send message failed:', error);
    },
  });
}

// Session hooks
export function useSessions() {
  return useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => apiClient.listSessions(),
    staleTime: 5000, // 5 seconds - shorter for dynamic titles
    refetchInterval: 15000, // 15 seconds - more frequent updates
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (request: { title?: string; metadata?: any }) => 
      apiClient.createSession(request),
    onSuccess: () => {
      // Invalidate sessions list to refresh after creation
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
    onError: (error) => {
      console.error('❌ Create session failed:', error);
    },
  });
}

export function useChat(sessionId?: string) {
  return useQuery({
    queryKey: queryKeys.chat(sessionId),
    queryFn: () => sessionId ? apiClient.getSession(sessionId) : Promise.resolve(null),
    enabled: !!sessionId,
    staleTime: 30000,
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (sessionId: string) => apiClient.deleteSession(sessionId),
    onSuccess: () => {
      // Invalidate sessions list to refresh after deletion
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
    onError: (error) => {
      console.error('❌ Delete session failed:', error);
    },
  });
}

export function useUpdateSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ sessionId, updates }: { sessionId: string; updates: { title?: string; metadata?: any } }) => 
      apiClient.updateSession(sessionId, updates),
    onSuccess: (data, variables) => {
      // Invalidate sessions list to refresh after update
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
      // Update specific session cache with the updated session data
      queryClient.setQueryData(queryKeys.chat(variables.sessionId), data);
    },
    onError: (error) => {
      console.error('❌ Update session failed:', error);
    },
  });
}

// Memory hooks
export function useSearchMemories(query: MemoryQuery, enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.memories(JSON.stringify(query)),
    queryFn: () => apiClient.searchMemories(query),
    enabled: enabled && !!query.query,
    staleTime: 60000, // 1 minute
  });
}

export function useSearchMemoriesMutation() {
  return useMutation({
    mutationFn: (query: MemoryQuery) => apiClient.searchMemories(query),
    onError: (error) => {
      console.error('❌ Search memories failed:', error);
    },
  });
}

// System health hooks
export function useSystemHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30000, // 30 seconds
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// Performance metrics hooks
export function usePerformanceMetrics() {
  return useQuery({
    queryKey: queryKeys.metrics,
    queryFn: () => apiClient.getMetrics(),
    refetchInterval: 60000, // 1 minute
    staleTime: 30000, // 30 seconds
  });
}

// Configuration hooks
export function useConfig() {
  return useQuery({
    queryKey: queryKeys.config,
    queryFn: () => apiClient.getConfig(),
    staleTime: 300000, // 5 minutes - config changes rarely
  });
}

// System Reset hook
export function useSystemReset() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => apiClient.resetSystem(),
    onSuccess: () => {
      // Clear all cached data after system reset
      queryClient.clear();
      
      // Force refresh of all data
      queryClient.invalidateQueries();
    },
    onError: (error) => {
      console.error('❌ System reset failed:', error);
    },
  });
}

// Connection status hook
export function useConnectionStatus() {
  return useQuery({
    queryKey: ['connection'],
    queryFn: () => apiClient.ping(),
    refetchInterval: 10000, // 10 seconds
    retry: false,
    staleTime: 5000, // 5 seconds
  });
}

// Custom hook for error handling
export function useApiError() {
  const handleError = (error: any): string => {
    return apiClient.handleApiError(error);
  };

  return { handleError };
}

// Custom hook for optimistic updates
export function useOptimisticChat(sessionId?: string) {
  const queryClient = useQueryClient();
  
  const addOptimisticMessage = (message: any) => {
    if (!sessionId) return;
    
    queryClient.setQueryData(
      queryKeys.chat(sessionId),
      (oldData: any) => {
        // Handle ConversationSession format
        if (oldData && oldData.messages && Array.isArray(oldData.messages)) {
          const optimisticMessage = {
            ...message,
            id: `temp-${Date.now()}`,
            timestamp: new Date().toISOString(),
            metadata: { ...message.metadata, optimistic: true }
          };
          return {
            ...oldData,
            messages: [...oldData.messages, optimisticMessage]
          };
        }
        return oldData;
      }
    );
  };

  const removeOptimisticMessage = (tempId: string) => {
    if (!sessionId) return;
    
    queryClient.setQueryData(
      queryKeys.chat(sessionId),
      (oldData: any) => {
        // Handle ConversationSession format
        if (oldData && oldData.messages && Array.isArray(oldData.messages)) {
          return {
            ...oldData,
            messages: oldData.messages.filter((msg: any) => msg.id !== tempId)
          };
        }
        return oldData;
      }
    );
  };

  return { addOptimisticMessage, removeOptimisticMessage };
}

// Utility hook for cache invalidation
export function useCacheUtils() {
  const queryClient = useQueryClient();

  const invalidateAll = () => {
    queryClient.invalidateQueries();
  };

  const invalidateSessions = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
  };

  const invalidateMetrics = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.metrics });
  };

  const clearCache = () => {
    queryClient.clear();
  };

  return {
    invalidateAll,
    invalidateSessions,
    invalidateMetrics,
    clearCache,
  };
}

// Hook for prefetching data
export function usePrefetch() {
  const queryClient = useQueryClient();

  const prefetchSessions = () => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.sessions,
      queryFn: () => apiClient.listSessions(),
      staleTime: 30000,
    });
  };

  const prefetchMetrics = () => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.metrics,
      queryFn: () => apiClient.getMetrics(),
      staleTime: 30000,
    });
  };

  return {
    prefetchSessions,
    prefetchMetrics,
  };
}
