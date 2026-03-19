'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useSidebar } from './sidebar-context'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { 
  Radio, 
  BarChart3, 
  ScrollText, 
  Settings, 
  PanelLeftClose,
  PanelLeft,
  X,
} from 'lucide-react'

const navLinks = [
  { href: '/', label: 'Mission Control', icon: Radio },
  { href: '/logs', label: 'Agent Logs', icon: ScrollText },
  { href: '/performance', label: 'Performance', icon: BarChart3 },
  { href: '/fleet', label: 'Fleet Hub', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { isExpanded, isMobileOpen, toggleSidebar, setMobileOpen } = useSidebar()
  
  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-screen flex-col border-r border-border bg-sidebar sidebar-transition',
          // Desktop
          'hidden md:flex',
          isExpanded ? 'w-60' : 'w-16',
          // Mobile
          'md:translate-x-0'
        )}
      >
        {/* Logo & Toggle */}
        <div className={cn(
          'flex h-14 items-center border-b border-border px-3',
          isExpanded ? 'justify-between' : 'justify-center'
        )}>
          {isExpanded ? (
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-orange">
                <Radio className="h-4 w-4 text-white" />
              </div>
              <span className="font-serif text-lg font-medium">
                <span className="gradient-text">SkyRescue</span>
                <span className="text-foreground"> AI</span>
              </span>
            </Link>
          ) : (
            <Link href="/" className="flex h-8 w-8 items-center justify-center rounded-lg gradient-orange">
              <Radio className="h-4 w-4 text-white" />
            </Link>
          )}
          
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className={cn('h-8 w-8 shrink-0', !isExpanded && 'hidden')}
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>

        {/* Toggle button when collapsed */}
        {!isExpanded && (
          <div className="flex justify-center py-3 border-b border-border">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="h-8 w-8"
            >
              <PanelLeft className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          <TooltipProvider delayDuration={0}>
            {navLinks.map((link) => {
              const isActive = pathname === link.href || 
                (link.href !== '/' && pathname.startsWith(link.href))
              const Icon = link.icon
              
              const linkContent = (
                <Link
                  href={link.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                    isExpanded ? 'justify-start' : 'justify-center',
                    isActive
                      ? 'bg-primary/10 text-primary border-l-2 border-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className={cn('h-5 w-5 shrink-0', isActive && 'text-primary')} />
                  {isExpanded && (
                    <span className="font-serif">{link.label}</span>
                  )}
                </Link>
              )

              if (!isExpanded) {
                return (
                  <Tooltip key={link.href}>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right" className="font-serif">
                      {link.label}
                    </TooltipContent>
                  </Tooltip>
                )
              }

              return <div key={link.href}>{linkContent}</div>
            })}
          </TooltipProvider>
        </nav>

        {/* Footer */}
        <div className={cn(
          'border-t border-border p-3',
          isExpanded ? 'text-left' : 'text-center'
        )}>
          {isExpanded ? (
            <p className="text-xs text-muted-foreground">
              SkyRescue AI v1.0
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">v1</p>
          )}
        </div>
      </aside>

      {/* Mobile Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-screen w-72 flex-col border-r border-border bg-sidebar transition-transform duration-300 md:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Mobile Header */}
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <Link href="/" className="flex items-center gap-2" onClick={() => setMobileOpen(false)}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-orange">
              <Radio className="h-4 w-4 text-white" />
            </div>
            <span className="font-serif text-lg font-medium">
              <span className="gradient-text">SkyRescue</span>
              <span className="text-foreground"> AI</span>
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen(false)}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Mobile Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {navLinks.map((link) => {
            const isActive = pathname === link.href || 
              (link.href !== '/' && pathname.startsWith(link.href))
            const Icon = link.icon
            
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-all',
                  isActive
                    ? 'bg-primary/10 text-primary border-l-2 border-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <Icon className={cn('h-5 w-5', isActive && 'text-primary')} />
                <span className="font-serif">{link.label}</span>
              </Link>
            )
          })}
        </nav>
      </aside>
    </>
  )
}
