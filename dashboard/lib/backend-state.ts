'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { AgentLogEntry, Drone, DroneStatus, LogType, MissionStatus } from '@/lib/mock-data'

export interface DashboardSummary {
  mission_status?: string
  mission_complete?: boolean
  elapsed_seconds?: number
  coverage_pct?: number
  found_survivors?: number
  total_survivors?: number
  sectors_scanned?: number
  total_scannable_sectors?: number
  discovered_fire_sectors?: number
  discovered_smoke_sectors?: number
  drone_count?: number
  active_drones?: number
  offline_drones?: number
  charging_drones?: number
  avg_battery_pct?: number
  mission_log_tail?: unknown[]
}

export interface DashboardStatePayload {
  connected: boolean
  last_update_unix: number | null
  error: string | null
  world: Record<string, unknown> | null
  summary: DashboardSummary | null
}

const API_BASE = 'http://localhost:8010'

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function toStringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function toDroneStatus(rawStatus: unknown): DroneStatus {
  const normalized = String(rawStatus || '').toLowerCase()
  if (normalized.includes('offline')) return 'offline'
  if (normalized.includes('charging')) return 'charging'
  if (normalized.includes('return')) return 'returning'
  if (normalized.includes('scan')) return 'scanning'
  return 'active'
}

function inferLogType(text: string): LogType {
  const t = text.toLowerCase()
  if (t.includes('critical') || t.includes('error') || t.includes('fail')) return 'warning'
  if (t.includes('mission start') || t.includes('mission started')) return 'trigger'
  if (t.includes('tool') || t.includes('scan') || t.includes('assign')) return 'tool_call'
  if (t.includes('detected') || t.includes('found') || t.includes('complete')) return 'result'
  return 'reasoning'
}

function parseLogMessage(entry: unknown): string {
  if (typeof entry === 'string') return entry
  if (isRecord(entry)) {
    const message = entry.message
    if (typeof message === 'string') return message
    const text = entry.text
    if (typeof text === 'string') return text
  }
  return String(entry)
}

export function normalizeMissionStatus(status: unknown): MissionStatus {
  const s = String(status || '').toLowerCase()
  if (s.includes('complete')) return 'completed'
  if (s.includes('pause')) return 'paused'
  if (s.includes('ready') || s.includes('idle')) return 'ready'
  return 'running'
}

export function toUiDrones(world: unknown): Drone[] {
  if (!isRecord(world) || !isRecord(world.drones)) return []

  return Object.entries(world.drones)
    .map(([id, value]) => {
      if (!isRecord(value)) return null

      const x = toNumber(value.x)
      const y = toNumber(value.y)
      const z = toNumber(value.z)
      const targetSector = toStringValue(value.current_target || value.target_sector || value.targetSector, '-')

      const drone: Drone = {
        id,
        name: toStringValue(value.name, id.replace(/_/g, '-').toUpperCase()),
        type: toStringValue(value.type, 'Rescue Drone'),
        status: toDroneStatus(value.status),
        battery: Math.max(0, Math.min(100, Math.round(toNumber(value.battery, 0)))),
        coordinates: { x, y, z },
        targetSector,
        lastSeen: 'live',
        ownerAgency: toStringValue(value.owner_agency || value.ownerAgency, 'SkyRescue'),
      }
      return drone
    })
    .filter((drone): drone is Drone => Boolean(drone))
}

export function toAgentLogEntries(logs: unknown): AgentLogEntry[] {
  if (!Array.isArray(logs)) return []

  return logs.slice(-80).map((item, index) => {
    const content = parseLogMessage(item)
    const timestamp = new Date(Date.now() - (logs.length - index) * 2000).toLocaleTimeString()
    return {
      id: `live-log-${index}`,
      timestamp,
      type: inferLogType(content),
      title: content.split(':')[0]?.slice(0, 42) || 'Mission Event',
      content,
    }
  })
}

export async function postMissionAction(
  action: 'start' | 'pause' | 'reset' | 'recall',
  payload: Record<string, unknown> = {}
): Promise<void> {
  let endpoint = ''
  if (action === 'start') endpoint = '/api/mission/start'
  if (action === 'pause') endpoint = '/api/mission/pause'
  if (action === 'reset') endpoint = '/api/mission/reset'
  if (action === 'recall') {
    const droneId = String(payload.drone_id || '')
    if (!droneId) throw new Error('drone_id is required for recall action')
    endpoint = `/api/drone/${encodeURIComponent(droneId)}/recall`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: action === 'reset' ? undefined : JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Action ${action} failed: ${response.status} ${text}`)
  }
}

export function useDashboardState(pollIntervalMs = 2000) {
  const [state, setState] = useState<DashboardStatePayload>({
    connected: false,
    last_update_unix: null,
    error: null,
    world: null,
    summary: null,
  })
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/state`, { cache: 'no-store' })
    if (!response.ok) {
      throw new Error(`Failed to fetch dashboard state (${response.status})`)
    }
    const payload = (await response.json()) as DashboardStatePayload
    setState(payload)
    setLoading(false)
  }, [])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        if (!cancelled) {
          await refresh()
        }
      } catch (error) {
        if (!cancelled) {
          setLoading(false)
          setState((prev: DashboardStatePayload) => ({
            ...prev,
            connected: false,
            error: error instanceof Error ? error.message : 'Failed to load dashboard state',
          }))
        }
      }
    }

    load()
    const timer = window.setInterval(load, pollIntervalMs)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [pollIntervalMs, refresh])

  const derived = useMemo(
    () => ({
      missionStatus: normalizeMissionStatus(state.summary?.mission_status),
      uiDrones: toUiDrones(state.world),
      missionLogs: toAgentLogEntries(state.world?.mission_log || state.summary?.mission_log_tail || []),
    }),
    [state.summary?.mission_status, state.summary?.mission_log_tail, state.world]
  )

  return { state, loading, refresh, ...derived }
}
