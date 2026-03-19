'use client'

import { cn } from '@/lib/utils'
import { SidebarProvider, useSidebar } from './sidebar-context'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'

interface AppShellProps {
  children: React.ReactNode
  title: string
  breadcrumb?: string
  missionStatus?: string
  fullScreen?: boolean
}

function AppShellContent({ 
  children, 
  title, 
  breadcrumb, 
  missionStatus,
  fullScreen = false 
}: AppShellProps) {
  const { isExpanded } = useSidebar()
  
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      
      {!fullScreen && (
        <Topbar 
          title={title} 
          breadcrumb={breadcrumb} 
          missionStatus={missionStatus}
        />
      )}
      
      <main
        className={cn(
          'transition-all duration-300',
          // Desktop offset for sidebar
          isExpanded ? 'md:ml-60' : 'md:ml-16',
          // Full screen mode
          fullScreen 
            ? 'h-screen' 
            : 'min-h-[calc(100vh-3.5rem)]'
        )}
      >
        {children}
      </main>
    </div>
  )
}

export function AppShell(props: AppShellProps) {
  return (
    <SidebarProvider>
      <AppShellContent {...props} />
    </SidebarProvider>
  )
}

// Export for full-screen pages that need custom topbar
export function FullScreenShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <div className="h-screen w-screen overflow-hidden bg-background">
        <Sidebar />
        {children}
      </div>
    </SidebarProvider>
  )
}
