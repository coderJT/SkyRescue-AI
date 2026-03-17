'use client'

import { useEffect, useState } from 'react'
import { FullScreenShell } from '@/components/layout/app-shell'
import { useSidebar } from '@/components/layout/sidebar-context'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { WorkflowCanvas } from '@/components/logs/workflow-canvas'
import {
  Search,
  FileJson,
  FileText,
  Table2,
  Zap,
  Brain,
  Terminal,
  GitBranch,
  CheckCircle,
  AlertTriangle,
  Play,
  Menu,
  PanelLeftClose,
  PanelLeft,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { agentLogEntries, missionHistory, type AgentLogEntry, type LogType } from '@/lib/mock-data'

const MCP_DASHBOARD_BASE_URL = process.env.NEXT_PUBLIC_MCP_DASHBOARD_URL || 'http://localhost:8000'

type DashboardLogsResponse = {
  mission_status?: string
  elapsed_seconds?: number
  coverage_pct?: number
  mission_log?: string[]
}

function inferLogType(message: string): LogType {
  const lower = message.toLowerCase()
  if (lower.includes('alert') || lower.includes('blocked') || lower.includes('error') || lower.includes('critical')) {
    return 'warning'
  }
  if (lower.startsWith('state:') || lower.includes('target set') || lower.includes('recalled') || lower.includes('moved to')) {
    return 'tool_call'
  }
  if (lower.includes('mission started') || lower.includes('simulation paused') || lower.includes('simulation resumed') || lower.includes('mission reset')) {
    return 'trigger'
  }
  if (lower.includes('mission complete') || lower.includes('found') || lower.includes('scanned sector')) {
    return 'result'
  }
  if (lower.includes('reason:')) {
    return 'condition'
  }
  return 'reasoning'
}

function inferTitle(message: string, type: LogType): string {
  if (type === 'tool_call') {
    if (message.toLowerCase().includes('target set')) return 'assign_target'
    if (message.toLowerCase().includes('moved to')) return 'move_to'
    if (message.toLowerCase().includes('recalled')) return 'recall_for_charging'
  }
  if (type === 'warning') return 'Warning Event'
  if (type === 'trigger') return 'Mission Event'
  if (type === 'result') return 'Mission Result'
  return 'Agent Reasoning'
}

function extractDroneId(message: string): string | undefined {
  const match = message.match(/(drone_\d+)/i)
  return match ? match[1].toLowerCase() : undefined
}

function toClockTime(referenceMs: number, reverseOffsetSeconds: number): string {
  const d = new Date(referenceMs - reverseOffsetSeconds * 1000)
  return d.toLocaleTimeString('en-GB', { hour12: false })
}

function mapDashboardLogsToEntries(logs: string[], elapsedSeconds: number): AgentLogEntry[] {
  const now = Date.now()
  const total = logs.length
  return logs.map((message, idx) => {
    const type = inferLogType(message)
    const secondsAgo = Math.max(0, elapsedSeconds - (total - 1 - idx))
    return {
      id: `live_${elapsedSeconds}_${idx}`,
      timestamp: toClockTime(now, secondsAgo),
      type,
      title: inferTitle(message, type),
      content: message,
      droneId: extractDroneId(message),
      metadata: {
        source: 'mcp-dashboard',
        index: idx,
      },
    }
  })
}

const nodeTypeFilters = [
  { value: 'trigger', label: 'Triggers', icon: Zap, color: 'text-emerald-600', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-200' },
  { value: 'reasoning', label: 'Reasoning', icon: Brain, color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
  { value: 'tool_call', label: 'Tool Calls', icon: Terminal, color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
  { value: 'condition', label: 'Conditions', icon: GitBranch, color: 'text-purple-600', bgColor: 'bg-purple-50', borderColor: 'border-purple-200' },
  { value: 'result', label: 'Results', icon: CheckCircle, color: 'text-indigo-600', bgColor: 'bg-indigo-50', borderColor: 'border-indigo-200' },
  { value: 'warning', label: 'Warnings', icon: AlertTriangle, color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200' },
]

function AgentLogsContent() {
  const { isExpanded, setMobileOpen } = useSidebar()
  const [selectedMission, setSelectedMission] = useState(missionHistory[0].id)
  const [liveEntries, setLiveEntries] = useState<AgentLogEntry[]>(agentLogEntries)
  const [isLiveConnected, setIsLiveConnected] = useState(false)
  const [isLoadingLive, setIsLoadingLive] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilters, setActiveFilters] = useState<Set<LogType>>(new Set())
  const [timeRange, setTimeRange] = useState('all')
  const [showCriticalPath, setShowCriticalPath] = useState(false)
  const [showBatteryImpact, setShowBatteryImpact] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [zoom, setZoom] = useState(1)

  useEffect(() => {
    let mounted = true

    const loadLogs = async () => {
      try {
        const response = await fetch(`${MCP_DASHBOARD_BASE_URL}/dashboard/logs`, {
          method: 'GET',
          cache: 'no-store',
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data: DashboardLogsResponse = await response.json()
        const rawLogs = Array.isArray(data.mission_log) ? data.mission_log : []
        const elapsed = Number(data.elapsed_seconds || 0)
        const mapped = mapDashboardLogsToEntries(rawLogs, elapsed)
        if (!mounted) return
        if (mapped.length > 0) {
          setLiveEntries(mapped)
        }
        setIsLiveConnected(true)
      } catch {
        if (!mounted) return
        setIsLiveConnected(false)
      } finally {
        if (mounted) setIsLoadingLive(false)
      }
    }

    loadLogs()
    const intervalId = window.setInterval(loadLogs, 2000)

    return () => {
      mounted = false
      window.clearInterval(intervalId)
    }
  }, [])

  // Filter entries based on search and active filters
  const filteredEntries = liveEntries.filter(entry => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch = 
        entry.title.toLowerCase().includes(query) ||
        entry.content.toLowerCase().includes(query) ||
        entry.droneId?.toLowerCase().includes(query) ||
        entry.type.toLowerCase().includes(query)
      if (!matchesSearch) return false
    }

    // Type filter
    if (activeFilters.size > 0 && !activeFilters.has(entry.type)) {
      return false
    }

    return true
  })

  const toggleFilter = (type: LogType) => {
    setActiveFilters(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  return (
    <div 
      className={cn(
        'flex h-screen transition-all duration-300',
        isExpanded ? 'md:ml-60' : 'md:ml-16'
      )}
    >
      {/* Left Sidebar - Filters & Options */}
      <aside
        className={cn(
          'h-full border-r border-border/40 bg-background/60 backdrop-blur transition-all duration-300 flex-shrink-0',
          sidebarOpen ? 'w-80' : 'w-0 overflow-hidden'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between border-b border-border/40 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-foreground">
              Filters & Options
            </h2>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setSidebarOpen(false)}
            >
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </div>

          {/* Mission Selector */}
          <div className="border-b border-border/40 p-4">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">
              Mission
            </Label>
            <Select value={selectedMission} onValueChange={setSelectedMission}>
              <SelectTrigger className="mt-2 font-mono text-sm">
                <SelectValue placeholder="Select mission" />
              </SelectTrigger>
              <SelectContent>
                {missionHistory.map((mission) => (
                  <SelectItem key={mission.id} value={mission.id} className="font-mono text-sm">
                    {mission.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Filter by Type */}
          <div className="border-b border-border/40 p-4">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-3 block">
              Node Types
            </Label>
            <div className="space-y-2">
              {nodeTypeFilters.map((filter) => {
                const Icon = filter.icon
                const isActive = activeFilters.has(filter.value as LogType)
                return (
                  <label
                    key={filter.value}
                    className={cn(
                      'flex items-center gap-3 rounded-lg border px-3 py-2 cursor-pointer transition-all',
                      isActive
                        ? `${filter.bgColor} ${filter.borderColor}`
                        : 'border-border hover:bg-muted/50'
                    )}
                  >
                    <Checkbox
                      checked={isActive}
                      onCheckedChange={() => toggleFilter(filter.value as LogType)}
                    />
                    <Icon className={cn('h-4 w-4', isActive ? filter.color : 'text-muted-foreground')} />
                    <span className={cn('text-sm', isActive ? filter.color : 'text-foreground')}>
                      {filter.label}
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* Time Range Filter */}
          <div className="border-b border-border/40 p-4">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-3 block">
              Time Range
            </Label>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="last-5min">Last 5 Minutes</SelectItem>
                <SelectItem value="last-15min">Last 15 Minutes</SelectItem>
                <SelectItem value="custom">Custom Range</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Search */}
          <div className="border-b border-border/40 p-4">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-3 block">
              Search
            </Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search nodes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-9 pl-9"
              />
            </div>
          </div>

          {/* Stats */}
          <div className="border-b border-border/40 p-4">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-3 block">
              Statistics
            </Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-muted/50 p-3 text-center">
                <p className="text-2xl font-semibold text-foreground">{filteredEntries.length}</p>
                <p className="text-xs text-muted-foreground">Nodes</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-3 text-center">
                <p className="text-2xl font-semibold text-primary">
                  {filteredEntries.filter(e => e.type === 'tool_call').length}
                </p>
                <p className="text-xs text-muted-foreground">Tool Calls</p>
              </div>
            </div>
          </div>

          {/* Export Options - Fixed at bottom */}
          <div className="mt-auto border-t border-border/40 p-4 bg-background/80 backdrop-blur">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-3 block">
              Export Format
            </Label>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1 gap-1">
                <FileJson className="h-3.5 w-3.5" />
                JSON
              </Button>
              <Button variant="outline" size="sm" className="flex-1 gap-1">
                <FileText className="h-3.5 w-3.5" />
                PDF
              </Button>
              <Button variant="outline" size="sm" className="flex-1 gap-1">
                <Table2 className="h-3.5 w-3.5" />
                CSV
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Canvas Area */}
      <div className="relative flex-1 h-full overflow-hidden">
        {/* Floating Top Bar */}
        <div className="absolute top-0 left-0 right-0 z-40 flex items-center justify-between p-4 bg-gradient-to-b from-background/95 via-background/80 to-transparent backdrop-blur-sm">
          <div className="flex items-center gap-3">
            {/* Mobile Menu */}
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 md:hidden"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>

            {/* Toggle Sidebar (when closed) */}
            {!sidebarOpen && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSidebarOpen(true)}
                className="gap-2"
              >
                <PanelLeft className="h-4 w-4" />
                Filters
              </Button>
            )}

            {/* Node Count */}
            <Badge variant="outline" className="font-mono text-xs gap-1">
              <Activity className="h-3 w-3" />
              {filteredEntries.length} nodes
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                'font-mono text-xs',
                isLiveConnected ? 'border-emerald-300 text-emerald-700' : 'border-amber-300 text-amber-700'
              )}
            >
              {isLoadingLive ? 'Connecting MCP...' : isLiveConnected ? 'Live MCP Logs' : 'Using Mock Logs'}
            </Badge>
          </div>

          {/* Canvas Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant={showCriticalPath ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowCriticalPath(!showCriticalPath)}
              className={cn(showCriticalPath && 'gradient-orange text-white')}
            >
              Show Critical Path
            </Button>
            <Button
              variant={showBatteryImpact ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowBatteryImpact(!showBatteryImpact)}
              className={cn(showBatteryImpact && 'gradient-orange text-white')}
            >
              Battery Impact
            </Button>
            <Button variant="outline" size="sm" className="gap-2">
              <Play className="h-4 w-4" />
              Replay Flow
            </Button>
          </div>
        </div>

        {/* Workflow Canvas */}
        <WorkflowCanvas 
          entries={filteredEntries} 
          zoom={zoom}
          onZoomChange={setZoom}
        />
      </div>
    </div>
  )
}

export default function AgentLogsPage() {
  return (
    <FullScreenShell>
      <AgentLogsContent />
    </FullScreenShell>
  )
}
