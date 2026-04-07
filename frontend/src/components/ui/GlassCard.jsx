import { cn } from '../../utils/cn';

export default function GlassCard({ children, className, ...props }) {
  return (
    <div 
      className={cn(
        "bg-surface-1/60 backdrop-blur-md border border-primary/15 rounded-2xl transition-all duration-300 hover:shadow-[0_0_20px_rgba(132,204,22,0.15)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
