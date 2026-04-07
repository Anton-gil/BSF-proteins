import { cn } from '../../utils/cn';

export default function Badge({ children, className }) {
  return (
    <span className={cn(
      "inline-block px-3 py-1 text-[10px] sm:text-xs font-semibold tracking-widest uppercase border rounded-full bg-primary/10 text-primary border-primary/30",
      className
    )}>
      {children}
    </span>
  );
}
