'use client'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useSidebar } from './sidebar-context'
import { Bell, Menu, User, Settings, LogOut } from 'lucide-react'

interface TopbarProps {
  title: string
  breadcrumb?: string
  missionStatus?: string
}

export function Topbar({ title, breadcrumb, missionStatus }: TopbarProps) {
  const { isExpanded, setMobileOpen } = useSidebar()
  
  return (
    <header
      className={cn(
        'sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 px-4 transition-all duration-300',
        // Desktop offset for sidebar
        'md:pl-4',
        isExpanded ? 'md:ml-60' : 'md:ml-16'
      )}
    >
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {/* Mobile Menu Button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 md:hidden"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Page Title */}
        <h1 className="font-serif text-xl font-medium text-foreground">
          {title}
        </h1>
      </div>

      {/* Center Section - Breadcrumb / Status */}
      <div className="hidden items-center gap-2 md:flex">
        {breadcrumb && (
          <span className="text-sm text-muted-foreground">{breadcrumb}</span>
        )}
        {missionStatus && (
          <Badge 
            variant="outline" 
            className={cn(
              'font-mono text-xs',
              missionStatus === 'running' && 'border-success bg-success/10 text-success',
              missionStatus === 'paused' && 'border-warning bg-warning/10 text-warning',
              missionStatus === 'ready' && 'border-muted-foreground bg-muted text-muted-foreground'
            )}
          >
            {missionStatus.toUpperCase()}
          </Badge>
        )}
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-3">
        {/* MCP Status */}
        <div className="hidden items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1.5 sm:flex">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <span className="font-mono text-xs text-muted-foreground">Connected</span>
        </div>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Bell className="h-5 w-5" />
        </Button>

        {/* User Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              <Avatar className="h-9 w-9">
                <AvatarImage src="/placeholder-avatar.jpg" alt="User" />
                <AvatarFallback className="bg-primary/10 text-primary font-medium">
                  OP
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium">Operator Admin</p>
                <p className="text-xs text-muted-foreground">admin@skyrescue.ai</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
