import { Lock, Cpu } from "lucide-react";

export default function PrivacyBadge() {
  return (
    <div 
      className="inline-flex items-center gap-4 px-5 py-3 bg-muted/40 rounded-sm"
      data-testid="badge-privacy-main"
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Lock className="w-4 h-4" />
        <span className="font-mono text-xs">Zero Data Retention</span>
      </div>
      <div className="w-px h-4 bg-border" />
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Cpu className="w-4 h-4" />
        <span className="font-mono text-xs">RAM-Only Processing</span>
      </div>
    </div>
  );
}
