import { cn } from '@/lib/utils'

interface SectionLabelProps {
  children: React.ReactNode
  pulse?: boolean
  className?: string
}

export function SectionLabel({ children, pulse = true, className }: SectionLabelProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-3 rounded-full border border-primary/30 bg-primary/5 px-5 py-2',
        className
      )}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
        </span>
      )}
      <span className="font-mono text-xs uppercase tracking-[0.15em] text-primary">
        {children}
      </span>
    </div>
  )
}
