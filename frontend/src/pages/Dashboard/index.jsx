import { NavLink, Outlet, Navigate, useLocation } from 'react-router-dom';
import { PlusCircle, CheckCircle, Clock } from 'lucide-react';
import { cn } from '../../utils/cn';
import PageTransition from '../../components/ui/PageTransition';
import { useBatchStore, getStageInfo } from '../../store/batchStore';

export default function Dashboard() {
  const location = useLocation();
  const { activeBatch, currentDay } = useBatchStore();

  const navItems = [
    { name: 'History', path: '/dashboard/history', icon: Clock },
    { name: 'Start New Batch', path: '/dashboard/new', icon: PlusCircle },
    { name: 'Daily Check-in', path: '/dashboard/checkin', icon: CheckCircle },
  ];

  // If at /dashboard exactly, redirect to the right page
  if (location.pathname === '/dashboard' || location.pathname === '/dashboard/') {
    return <Navigate to={activeBatch ? '/dashboard/checkin' : '/dashboard/new'} replace />;
  }

  const stage = activeBatch ? getStageInfo(currentDay) : null;

  return (
    <PageTransition className="h-[calc(100vh-64px)] flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-surface-1 flex flex-col shrink-0">
        <div className="p-6">
          <h2 className="text-xs uppercase tracking-widest text-text-muted font-bold mb-4">Dashboard</h2>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-medium border-l-2",
                    isActive
                      ? "bg-primary/10 text-primary border-primary"
                      : "text-text-muted hover:text-text hover:bg-surface-2 border-transparent"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.name}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Active batch pill — driven by real store data */}
        <div className="mt-auto p-6 border-t border-border">
          <div className="text-xs uppercase tracking-widest text-text-muted font-bold mb-3">Active Batch</div>
          {activeBatch ? (
            <div className="flex items-center gap-3 bg-surface-2 p-3 rounded-lg border border-border">
              <div className="w-2 h-2 rounded-full bg-primary shadow-glow animate-pulse" />
              <div>
                <div className="text-sm font-bold text-accent">Batch #{activeBatch.id?.slice(-4)}</div>
                <div className="text-xs text-text-muted">
                  Day {currentDay} · {stage?.emoji} {stage?.focus}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 bg-surface-2 p-3 rounded-lg border border-border opacity-50">
              <div className="w-2 h-2 rounded-full bg-text-muted" />
              <div>
                <div className="text-sm font-bold text-text-muted">No Active Batch</div>
                <div className="text-xs text-text-muted">Start one to begin</div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto bg-bg relative">
        <Outlet />
      </main>
    </PageTransition>
  );
}
