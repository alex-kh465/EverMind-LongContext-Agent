/**
 * Main Layout Component
 * Provides navigation and consistent page structure
 */

import { Link, useLocation } from 'react-router-dom';
import {
  ChatBubbleLeftRightIcon,
  CircleStackIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Memory', href: '/memory', icon: CircleStackIcon },
  { name: 'Metrics', href: '/metrics', icon: ChartBarIcon },
];

function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">LC</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">LongContext</h1>
              <p className="text-sm text-gray-500">Agent</p>
            </div>
          </div>
        </div>

        <nav className="mt-8">
          <div className="px-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href || 
                              (item.href === '/chat' && location.pathname === '/');
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors relative
                    ${
                      isActive
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:text-primary-600 hover:bg-gray-100'
                    }
                  `}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-primary-50 rounded-lg"
                      initial={false}
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <item.icon
                    className={`
                      mr-3 h-5 w-5 flex-shrink-0 relative z-10
                      ${
                        isActive
                          ? 'text-primary-600'
                          : 'text-gray-400 group-hover:text-primary-600'
                      }
                    `}
                  />
                  <span className="relative z-10">{item.name}</span>
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
          <div className="text-xs text-gray-500 text-center">
            <p>LongContext Agent v1.0</p>
            <p className="mt-1">Resilient Memory System</p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

export default Layout;
