import { Lock } from "lucide-react";

export default function Header() {
  return (
    <header 
      className="sticky top-0 z-50 bg-background border-b h-20 flex items-center justify-between px-6 md:px-12"
      data-testid="header"
    >
      <div className="flex items-center gap-2">
        <span 
          className="font-serif text-xl font-bold tracking-widest uppercase"
          data-testid="text-header-logo"
        >
          ULISSE
        </span>
      </div>
      
      <div 
        className="flex items-center gap-2 px-4 py-2 bg-muted/50 rounded-sm text-sm text-muted-foreground"
        data-testid="badge-privacy-header"
      >
        <Lock className="w-4 h-4" />
        <span className="hidden sm:inline font-mono text-xs">Zero Data Retention</span>
      </div>
    </header>
  );
}
