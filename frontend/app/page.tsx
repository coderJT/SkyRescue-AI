'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { FullScreenShell } from '@/components/layout/app-shell'
import { useSidebar } from '@/components/layout/sidebar-context'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import {
  Play,
  Pause,
  RotateCcw,
  Zap,
  Copy,
  Check,
  Menu,
  Radio,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  drones,
  currentMission,
  type MissionStatus,
} from '@/lib/mock-data'

const MCP_DASHBOARD_BASE_URL = process.env.NEXT_PUBLIC_MCP_DASHBOARD_URL || 'http://localhost:8000'

type DashboardWorldStateResponse = {
  mission_status?: 'waiting' | 'active' | 'success' | 'failure'
  elapsed_seconds?: number
}

function formatTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function MissionControlContent() {
  const router = useRouter()
  const { isExpanded, setMobileOpen } = useSidebar()
  const [missionStatus, setMissionStatus] = useState<MissionStatus>(currentMission.status)
  const [elapsedTime, setElapsedTime] = useState(currentMission.elapsedTime)
  const [speedMultiplier, setSpeedMultiplier] = useState(1)
  const [copied, setCopied] = useState(false)
  const hasAutoRedirectedRef = useRef(false)

  // Timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (missionStatus === 'running') {
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1)
      }, 1000 / speedMultiplier)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [missionStatus, speedMultiplier])

  // Keep mission status synced with backend and redirect to dashboard when mission finishes.
  useEffect(() => {
    let mounted = true

    const loadMissionState = async () => {
      try {
        const response = await fetch(`${MCP_DASHBOARD_BASE_URL}/dashboard/world-state`, {
          method: 'GET',
          cache: 'no-store',
        })
        if (!response.ok) return

        const data: DashboardWorldStateResponse = await response.json()
        if (!mounted) return

        if (typeof data.elapsed_seconds === 'number') {
          setElapsedTime(Math.max(0, Math.floor(data.elapsed_seconds)))
        }

        if (data.mission_status === 'active') {
          setMissionStatus('running')
        } else if (data.mission_status === 'waiting') {
          setMissionStatus('ready')
        } else if (data.mission_status === 'success' || data.mission_status === 'failure') {
          setMissionStatus('completed')
          if (!hasAutoRedirectedRef.current) {
            hasAutoRedirectedRef.current = true
            router.push('/logs')
          }
        }
      } catch {
        // If backend is unavailable, keep current local UI state.
      }
    }

    loadMissionState()
    const intervalId = window.setInterval(loadMissionState, 2000)

    return () => {
      mounted = false
      window.clearInterval(intervalId)
    }
  }, [router])

  const handleCopyMissionId = () => {
    navigator.clipboard.writeText(currentMission.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleStart = () => setMissionStatus('running')
  const handlePause = () => setMissionStatus('paused')
  const handleReset = () => {
    setMissionStatus('ready')
    setElapsedTime(0)
  }

  const speedLabel = speedMultiplier === 1 ? '1x' : speedMultiplier === 2 ? '2x' : speedMultiplier === 5 ? '5x' : `${speedMultiplier}x`

  return (
    <div 
      className={cn(
        'relative h-screen w-full overflow-hidden transition-all duration-300',
        isExpanded ? 'md:ml-60' : 'md:ml-16'
      )}
    >
      {/* Top Bar Overlay */}
      <div className="absolute top-0 left-0 right-0 z-50 bg-gradient-to-b from-background/95 via-background/80 to-transparent backdrop-blur-sm">
        <div className="flex h-14 items-center justify-between px-4">
          {/* Left: Mobile menu + Mission Info */}
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

            {/* Mission ID Pill */}
            <button
              onClick={handleCopyMissionId}
              className="group inline-flex items-center gap-2 rounded-lg border border-border bg-card/80 px-3 py-1.5 font-mono text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5"
            >
              <span>{currentMission.id}</span>
              {copied ? (
                <Check className="h-3.5 w-3.5 text-success" />
              ) : (
                <Copy className="h-3.5 w-3.5 opacity-50 group-hover:opacity-100" />
              )}
            </button>

            {/* Status Badge */}
            <Badge
              className={cn(
                'capitalize',
                missionStatus === 'running' && 'gradient-orange text-white',
                missionStatus === 'paused' && 'bg-warning/10 text-warning border-warning/30',
                missionStatus === 'ready' && 'bg-muted text-muted-foreground'
              )}
            >
              {missionStatus}
            </Badge>
          </div>

          {/* Center: Timer */}
          <div
            className={cn(
              'font-mono text-3xl font-semibold tracking-tight',
              missionStatus === 'running' ? 'text-primary' : 'text-foreground'
            )}
          >
            {formatTime(elapsedTime)}
          </div>

          {/* Right: MCP Status */}
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-1.5 sm:flex">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              <span className="font-mono text-xs text-muted-foreground">MCP Connected</span>
            </div>
          </div>
        </div>
      </div>

      {/* Full-Screen Simulation Viewer */}
      <div className="h-full w-full">
        {/* Placeholder for Three.js simulation */}
        <div className="relative h-full w-full dot-pattern bg-muted/30">
          {/* Grid overlay with simulated content */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-3xl gradient-orange shadow-accent-lg">
                <Radio className="h-12 w-12 text-white" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-foreground">
                3D Simulation Viewer
              </h2>
              <p className="mt-2 max-w-md text-muted-foreground">
                Embed React Three Fiber canvas here. The simulation shows the drone swarm navigating the disaster zone in real-time.
              </p>
            </div>
          </div>

          {/* Simulated drone positions overlay */}
          {drones.map((drone) => (
            <div
              key={drone.id}
              className={cn(
                'absolute flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white transition-all',
                drone.status === 'active' && 'gradient-orange shadow-accent animate-pulse',
                drone.status === 'scanning' && 'bg-info',
                drone.status === 'returning' && 'bg-warning',
                drone.status === 'charging' && 'bg-muted text-muted-foreground',
                drone.status === 'offline' && 'bg-error'
              )}
              style={{
                left: `${20 + (drone.coordinates.x / 100) * 60}%`,
                top: `${20 + (drone.coordinates.y / 100) * 60}%`,
              }}
              title={`${drone.id} - ${drone.status} (${drone.battery}%)`}
            >
              {drone.id.split('-')[1]}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom-Right Floating Controls */}
      <div className="absolute bottom-6 right-6 z-40 flex flex-col items-end gap-3">
        {/* Speed Control */}
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm">
          <span className="text-sm font-medium text-muted-foreground">Speed</span>
          <div className="w-32">
            <Slider
              value={[speedMultiplier]}
              onValueChange={(v) => setSpeedMultiplier(v[0])}
              min={0.5}
              max={5}
              step={0.5}
              className="w-full"
            />
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            {speedLabel}
          </Badge>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Playback Controls */}
          <div className="flex gap-2 rounded-xl border border-border bg-card/95 p-2 shadow-lg backdrop-blur-sm">
            <Button
              size="icon"
              variant={missionStatus === 'running' ? 'secondary' : 'default'}
              onClick={handleStart}
              disabled={missionStatus === 'running'}
              className={cn(
                'h-10 w-10',
                missionStatus !== 'running' && 'gradient-orange text-white shadow-accent hover:brightness-110'
              )}
            >
              <Play className="h-5 w-5" />
            </Button>
            <Button
              size="icon"
              variant="outline"
              onClick={handlePause}
              disabled={missionStatus !== 'running'}
              className="h-10 w-10"
            >
              <Pause className="h-5 w-5" />
            </Button>
            <Button
              size="icon"
              variant="outline"
              onClick={handleReset}
              className="h-10 w-10"
            >
              <RotateCcw className="h-5 w-5" />
            </Button>
          </div>

          {/* KILL Button */}
          <Button
            size="lg"
            className="h-12 bg-error px-6 text-white shadow-lg hover:bg-error/90"
          >
            <Zap className="mr-2 h-5 w-5" />
            KILL
          </Button>
        </div>
      </div>

      {/* Bottom-Left Stats Overlay */}
      <div className="absolute bottom-6 left-6 z-40">
        <div className="flex gap-3">
          {/* Coverage */}
          <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Coverage</p>
            <p className="text-2xl font-semibold text-primary">{currentMission.coverage}%</p>
          </div>
          
          {/* Survivors */}
          <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Survivors</p>
            <p className="text-2xl font-semibold text-success">{currentMission.survivorsFound}/{currentMission.totalSurvivors}</p>
          </div>

          {/* Active Drones */}
          <div className="hidden rounded-xl border border-border bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm sm:block">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Active Drones</p>
            <p className="text-2xl font-semibold text-foreground">
              {drones.filter(d => d.status === 'active' || d.status === 'scanning').length}/{drones.length}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function MissionControlPage() {
  return (
    <FullScreenShell>
      <MissionControlContent />
    </FullScreenShell>
  )
}
