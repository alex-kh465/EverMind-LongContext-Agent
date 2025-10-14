import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Pages
import ChatPage from './pages/ChatPage';
import MemoryPage from './pages/MemoryPage';
import MetricsPage from './pages/MetricsPage';

// Components
import Layout from './components/Layout';
import ConnectionStatus from './components/ConnectionStatus';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Don't retry on 404s or if we've already retried 3 times
        if (error?.response?.status === 404 || failureCount >= 3) {
          return false;
        }
        return true;
      },
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-900">
          <ConnectionStatus />
          <Routes>
            {/* Chat routes use their own layout */}
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:sessionId" element={<ChatPage />} />
            
            {/* Other routes use the main layout */}
            <Route path="/memory" element={
              <Layout>
                <MemoryPage />
              </Layout>
            } />
            <Route path="/metrics" element={
              <Layout>
                <MetricsPage />
              </Layout>
            } />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
