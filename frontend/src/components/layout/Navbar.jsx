import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'About', path: '/about' },
    { name: 'Dashboard', path: '/dashboard/history' }, // Default dashboard route
    { name: 'Report', path: '/report' },
  ];

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 h-16 transition-all duration-300 ease-in-out',
        scrolled
          ? 'bg-[#050a05]/80 backdrop-blur-md border-b border-border'
          : 'bg-transparent border-b border-transparent'
      )}
    >
      <div className="container mx-auto px-6 h-full flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <img 
            src="/logo.png" 
            alt="BSF Optimizer" 
            className="w-8 h-8 object-contain"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <span className="font-display font-bold text-xl tracking-tight text-text group-hover:text-primary transition-colors">
            BSF Optimizer
          </span>
        </Link>
        
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                'text-sm font-medium transition-colors hover:text-primary-bright',
                location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path))
                  ? 'text-primary'
                  : 'text-text-muted'
              )}
            >
              {link.name}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <Link
            to="/dashboard/new"
            className="hidden sm:inline-flex items-center justify-center px-5 py-2 text-sm font-medium rounded-lg bg-primary text-[#050a05] hover:bg-primary-bright transition-all hover:scale-105 active:scale-95"
            style={{ boxShadow: '0 0 15px rgba(132, 204, 22, 0.2)' }}
          >
            Start Batch
          </Link>
        </div>
      </div>
    </header>
  );
}
