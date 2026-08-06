/**
 * AI Studio Navigation Sidebar
 *
 * Quick access to all AI Intelligence modules
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function StudioSidebar() {
  const pathname = usePathname();

  const modules = [
    {
      id: 'hub',
      title: 'Dashboard',
      icon: '📊',
      href: '/studio',
      description: 'Overview & quick stats',
    },
    {
      id: 'answer-engine',
      title: 'Answer Engine',
      icon: '🔍',
      href: '/studio/answer-engine',
      description: 'Brand mentions',
    },
    {
      id: 'agent-analytics',
      title: 'Agent Analytics',
      icon: '🤖',
      href: '/studio/agent-analytics',
      description: 'Bot traffic',
    },
    {
      id: 'prompt-volumes',
      title: 'Prompt Volumes',
      icon: '📈',
      href: '/studio/prompt-volumes',
      description: 'Keywords',
    },
    {
      id: 'brands',
      title: 'Brand Hub',
      icon: '🏢',
      href: '/studio/brands',
      description: 'Your brands',
    },
  ];

  const isActive = (href: string) => {
    if (href === '/studio') {
      return pathname === '/studio' || pathname === '/studio/';
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="bg-white border-r border-gray-200 w-64 min-h-screen p-4">
      <div className="mb-8">
        <div className="text-2xl font-bold text-gray-900">AI Studio</div>
        <div className="text-xs text-gray-600">Intelligence Platform</div>
      </div>

      <nav className="space-y-2">
        {modules.map((module) => (
          <Link
            key={module.id}
            href={module.href}
            className={`flex items-start gap-3 px-3 py-3 rounded-lg transition ${
              isActive(module.href) ? 'bg-blue-50 border-l-4 border-[var(--brand)]' : 'hover:bg-gray-50'
            }`}
          >
            <span className="text-xl flex-shrink-0 mt-0.5">{module.icon}</span>
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-900">{module.title}</div>
              <div className="text-xs text-gray-600">{module.description}</div>
            </div>
          </Link>
        ))}
      </nav>

      {/* Help Section */}
      <div className="mt-8 pt-8 border-t border-gray-200">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-sm font-semibold text-blue-900 mb-2">💡 Pro Tip</div>
          <div className="text-xs text-blue-800">
            Use the dashboard overview to see all metrics at a glance, then dive into specific modules for detailed
            analysis.
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-8 border-t border-gray-200 text-xs text-gray-600">
        <div>Version: 2.0</div>
        <div>Last sync: just now</div>
      </div>
    </aside>
  );
}

/**
 * Page wrapper with sidebar
 */
export function StudioLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <StudioSidebar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
