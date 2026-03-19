// SkyRescue AI - Mock Data

export type DroneStatus = 'active' | 'charging' | 'offline' | 'returning' | 'scanning'
export type HazardType = 'fire' | 'smoke' | 'no-fly' | 'clear' | 'scanned'
export type EventType = 'critical' | 'warning' | 'info' | 'success'
export type MissionStatus = 'ready' | 'running' | 'paused' | 'completed'
export type LogType = 'trigger' | 'reasoning' | 'tool_call' | 'condition' | 'result' | 'warning'

export interface Drone {
  id: string
  name: string
  type: string
  status: DroneStatus
  battery: number
  coordinates: { x: number; y: number; z: number }
  targetSector: string
  lastSeen: string
  ownerAgency: string
}

export interface MissionEvent {
  id: string
  timestamp: string
  type: EventType
  message: string
  droneId?: string
  sector?: string
}

export interface Survivor {
  id: string
  sector: string
  hazardType: HazardType
  foundAt: string
  rescuedAt?: string
  droneId: string
  coordinates: { x: number; y: number }
}

export interface GridSector {
  id: string
  row: number
  col: number
  hazard: HazardType
  scanned: boolean
  survivors: number
}

export interface Mission {
  id: string
  name: string
  status: MissionStatus
  startedAt: string
  endedAt?: string
  coverage: number
  survivorsFound: number
  totalSurvivors: number
  avgBattery: number
  elapsedTime: number // in seconds
}

export interface AgentLogEntry {
  id: string
  timestamp: string
  type: LogType
  title: string
  content: string
  droneId?: string
  toolArgs?: Record<string, unknown>
  executionTime?: number
  result?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface Agency {
  id: string
  name: string
  country: string
  countryCode: string
  connected: boolean
  dataSharing: boolean
  drones: number
}

export interface MissionPreset {
  id: string
  name: string
  disasterType: string
  icon: string
  config: {
    droneCount: number
    scanPattern: string
    priorityZones: string[]
    batteryThreshold: number
  }
}

export interface Bottleneck {
  id: string
  severity: 'high' | 'medium' | 'low'
  title: string
  description: string
  impact: number
  recommendation: string
  affectedDrones: string[]
}

export interface Recommendation {
  id: string
  rank: number
  impact: 'high' | 'medium' | 'low'
  title: string
  description: string
}

// Mock Drones
export const drones: Drone[] = [
  {
    id: 'drone_1',
    name: 'Alpha-1',
    type: 'Recon Scout',
    status: 'active',
    battery: 87,
    coordinates: { x: 234.5, y: 156.2, z: 45.0 },
    targetSector: '2_3',
    lastSeen: '2 sec ago',
    ownerAgency: 'BNPB',
  },
  {
    id: 'drone_2',
    name: 'Beta-2',
    type: 'Thermal Scanner',
    status: 'scanning',
    battery: 72,
    coordinates: { x: 312.8, y: 89.4, z: 52.0 },
    targetSector: '4_5',
    lastSeen: '1 sec ago',
    ownerAgency: 'BNPB',
  },
  {
    id: 'drone_3',
    name: 'Gamma-3',
    type: 'Heavy Lifter',
    status: 'returning',
    battery: 18,
    coordinates: { x: 45.2, y: 278.9, z: 30.0 },
    targetSector: 'base',
    lastSeen: '3 sec ago',
    ownerAgency: 'NADMA',
  },
  {
    id: 'drone_4',
    name: 'Delta-4',
    type: 'Recon Scout',
    status: 'active',
    battery: 95,
    coordinates: { x: 189.3, y: 201.7, z: 48.0 },
    targetSector: '7_8',
    lastSeen: '1 sec ago',
    ownerAgency: 'NADMA',
  },
  {
    id: 'drone_5',
    name: 'Echo-5',
    type: 'Thermal Scanner',
    status: 'charging',
    battery: 45,
    coordinates: { x: 10.0, y: 10.0, z: 0.0 },
    targetSector: '-',
    lastSeen: '5 min ago',
    ownerAgency: 'BFAR',
  },
]

// Mock Mission Events
export const missionEvents: MissionEvent[] = [
  {
    id: 'evt_1',
    timestamp: '10:23:45',
    type: 'critical',
    message: 'Survivor detected in sector 3_4 (fire zone)',
    droneId: 'drone_1',
    sector: '3_4',
  },
  {
    id: 'evt_2',
    timestamp: '10:23:42',
    type: 'warning',
    message: 'drone_3 battery critical (18%) - returning to base',
    droneId: 'drone_3',
  },
  {
    id: 'evt_3',
    timestamp: '10:23:38',
    type: 'success',
    message: 'Sector 2_3 scan complete - 2 survivors found',
    droneId: 'drone_2',
    sector: '2_3',
  },
  {
    id: 'evt_4',
    timestamp: '10:23:30',
    type: 'info',
    message: 'Initiating thermal scan on sector 4_5',
    droneId: 'drone_2',
    sector: '4_5',
  },
  {
    id: 'evt_5',
    timestamp: '10:23:22',
    type: 'warning',
    message: 'No-fly zone detected in sector 6_6 - rerouting',
    droneId: 'drone_4',
    sector: '6_6',
  },
  {
    id: 'evt_6',
    timestamp: '10:23:15',
    type: 'info',
    message: 'Mission coverage reached 50%',
  },
  {
    id: 'evt_7',
    timestamp: '10:23:08',
    type: 'critical',
    message: 'Multiple heat signatures in sector 7_8',
    droneId: 'drone_4',
    sector: '7_8',
  },
  {
    id: 'evt_8',
    timestamp: '10:23:01',
    type: 'success',
    message: 'Survivor extraction team dispatched to sector 3_4',
    sector: '3_4',
  },
]

// Mock Grid Sectors (10x10)
export const gridSectors: GridSector[] = Array.from({ length: 100 }, (_, i) => {
  const row = Math.floor(i / 10)
  const col = i % 10
  const hazards: HazardType[] = ['clear', 'clear', 'clear', 'fire', 'smoke', 'no-fly']
  const randomHazard = hazards[Math.floor(Math.random() * hazards.length)]
  
  // Pre-define some specific hazard zones
  const fireZones = ['2_3', '4_5', '7_8']
  const smokeZones = ['2_4', '3_3', '4_4', '5_5', '7_7']
  const noFlyZones = ['6_6', '0_0', '9_9']
  
  const sectorId = `${row}_${col}`
  
  let hazard: HazardType = 'clear'
  if (fireZones.includes(sectorId)) hazard = 'fire'
  else if (smokeZones.includes(sectorId)) hazard = 'smoke'
  else if (noFlyZones.includes(sectorId)) hazard = 'no-fly'
  
  const scanned = Math.random() > 0.33
  
  return {
    id: sectorId,
    row,
    col,
    hazard: scanned ? (hazard === 'clear' ? 'scanned' : hazard) : hazard,
    scanned,
    survivors: hazard === 'fire' || hazard === 'smoke' ? Math.floor(Math.random() * 3) : 0,
  }
})

// Mock Current Mission
export const currentMission: Mission = {
  id: 'MSN-2024-0312-001',
  name: 'Peatland Fire Response - Riau',
  status: 'running',
  startedAt: '2024-03-12T10:00:00Z',
  coverage: 67,
  survivorsFound: 12,
  totalSurvivors: 17,
  avgBattery: 78,
  elapsedTime: 734, // 12:14
}

// Mock Historical Missions
export const missionHistory: Mission[] = [
  currentMission,
  {
    id: 'MSN-2024-0311-002',
    name: 'Flash Flood Rescue - Johor',
    status: 'completed',
    startedAt: '2024-03-11T14:30:00Z',
    endedAt: '2024-03-11T17:45:00Z',
    coverage: 100,
    survivorsFound: 8,
    totalSurvivors: 8,
    avgBattery: 42,
    elapsedTime: 11700,
  },
  {
    id: 'MSN-2024-0310-001',
    name: 'Earthquake Assessment - Mindanao',
    status: 'completed',
    startedAt: '2024-03-10T08:00:00Z',
    endedAt: '2024-03-10T14:20:00Z',
    coverage: 95,
    survivorsFound: 23,
    totalSurvivors: 25,
    avgBattery: 35,
    elapsedTime: 22800,
  },
  {
    id: 'MSN-2024-0308-001',
    name: 'Urban SAR - Jakarta',
    status: 'completed',
    startedAt: '2024-03-08T09:15:00Z',
    endedAt: '2024-03-08T12:30:00Z',
    coverage: 100,
    survivorsFound: 5,
    totalSurvivors: 5,
    avgBattery: 67,
    elapsedTime: 11700,
  },
]

// Mock Agent Log Entries (Chain-of-Thought)
export const agentLogEntries: AgentLogEntry[] = [
  {
    id: 'log_1',
    timestamp: '10:23:45',
    type: 'trigger',
    title: 'Mission Start',
    content: 'Mission MSN-2024-0312-001 initiated. Peatland fire response activated with 5 drones.',
    metadata: {
      missionId: 'MSN-2024-0312-001',
      activeDrones: 5,
    },
  },
  {
    id: 'log_2',
    timestamp: '10:23:46',
    type: 'reasoning',
    title: 'Fleet Assessment',
    content: '5 drones active with average battery at 87%. Optimal for full coverage scan. Prioritizing high-risk sectors based on satellite thermal data.',
    droneId: 'all',
    metadata: {
      avgBattery: 87,
      sectorsToScan: 100,
      estimatedTime: '45 min',
    },
  },
  {
    id: 'log_3',
    timestamp: '10:23:47',
    type: 'condition',
    title: 'Hazard Priority Check',
    content: 'Detected 3 fire zones (sectors 2_3, 4_5, 7_8) and 5 smoke zones adjacent. Fire zones prioritized due to 60s survival window in active fire.',
    metadata: {
      fireZones: ['2_3', '4_5', '7_8'],
      smokeZones: ['2_4', '3_3', '4_4', '5_5', '7_7'],
      hazardPriority: 'fire > smoke > clear',
    },
  },
  {
    id: 'log_4',
    timestamp: '10:23:48',
    type: 'tool_call',
    title: 'scan_sector',
    content: 'Executing thermal scan on high-priority fire zone sector 2_3.',
    droneId: 'drone_1',
    toolArgs: {
      drone_id: 'drone_1',
      sector_id: '2_3',
      scan_type: 'thermal',
    },
    executionTime: 4.2,
    result: {
      survivors_found: 2,
      battery_remaining: 89.5,
      hazard_type: 'fire',
      confidence: 0.94,
    },
  },
  {
    id: 'log_5',
    timestamp: '10:23:52',
    type: 'result',
    title: 'Survivors Detected',
    content: '2 survivors located in sector 2_3 (fire zone). GPS coordinates logged. Extraction team notified.',
    droneId: 'drone_1',
    metadata: {
      survivors: 2,
      sector: '2_3',
      coordinates: [
        { lat: -0.4928, lng: 101.7068 },
        { lat: -0.4931, lng: 101.7072 },
      ],
    },
  },
  {
    id: 'log_6',
    timestamp: '10:23:55',
    type: 'tool_call',
    title: 'move_to',
    content: 'Repositioning drone_2 to sector 4_5 for thermal scan.',
    droneId: 'drone_2',
    toolArgs: {
      drone_id: 'drone_2',
      target_sector: '4_5',
      speed: 'fast',
    },
    executionTime: 2.1,
    result: {
      status: 'success',
      eta: '12 seconds',
      battery_impact: -1.2,
    },
  },
  {
    id: 'log_7',
    timestamp: '10:24:01',
    type: 'warning',
    title: 'Battery Critical',
    content: 'drone_3 battery at 18%. Below safe threshold (20%). Initiating return-to-base protocol.',
    droneId: 'drone_3',
    metadata: {
      battery: 18,
      threshold: 20,
      distanceToBase: '450m',
      estimatedReturn: '90 seconds',
    },
  },
  {
    id: 'log_8',
    timestamp: '10:24:05',
    type: 'tool_call',
    title: 'recall_drone',
    content: 'Executing emergency recall for drone_3 due to critical battery.',
    droneId: 'drone_3',
    toolArgs: {
      drone_id: 'drone_3',
      reason: 'battery_critical',
      priority: 'high',
    },
    executionTime: 0.8,
    result: {
      status: 'returning',
      eta: '87 seconds',
      coverage_impact: '-3%',
    },
  },
  {
    id: 'log_9',
    timestamp: '10:24:10',
    type: 'reasoning',
    title: 'Coverage Rebalancing',
    content: 'With drone_3 returning, redistributing sector assignments. drone_4 will cover sectors 5_6 through 6_8. drone_1 continues fire zone priority scan.',
    droneId: 'all',
    metadata: {
      reassignments: {
        drone_4: ['5_6', '5_7', '6_7', '6_8'],
        drone_1: ['3_3', '3_4'],
      },
      coverageProjection: '94%',
    },
  },
  {
    id: 'log_10',
    timestamp: '10:24:15',
    type: 'tool_call',
    title: 'scan_sector',
    content: 'Initiating thermal scan on sector 4_5 after drone_2 arrival.',
    droneId: 'drone_2',
    toolArgs: {
      drone_id: 'drone_2',
      sector_id: '4_5',
      scan_type: 'thermal',
    },
    executionTime: 3.8,
    result: {
      survivors_found: 3,
      battery_remaining: 68.2,
      hazard_type: 'fire',
      confidence: 0.91,
    },
  },
  {
    id: 'log_11',
    timestamp: '10:24:20',
    type: 'result',
    title: 'Multiple Survivors Found',
    content: '3 additional survivors detected in sector 4_5. Total survivors now at 5. Updating mission dashboard.',
    droneId: 'drone_2',
    metadata: {
      newSurvivors: 3,
      totalSurvivors: 5,
      sector: '4_5',
    },
  },
  {
    id: 'log_12',
    timestamp: '10:24:25',
    type: 'condition',
    title: 'No-Fly Zone Check',
    content: 'drone_4 approaching sector 6_6. Detected as restricted airspace (active power lines). Rerouting required.',
    droneId: 'drone_4',
    metadata: {
      restrictedSector: '6_6',
      reason: 'power_lines',
      alternateRoute: ['5_7', '6_7', '7_6'],
    },
  },
  {
    id: 'log_13',
    timestamp: '10:24:30',
    type: 'tool_call',
    title: 'update_route',
    content: 'Updating flight path for drone_4 to avoid no-fly zone at sector 6_6.',
    droneId: 'drone_4',
    toolArgs: {
      drone_id: 'drone_4',
      avoid_sectors: ['6_6'],
      new_route: ['5_7', '6_7', '7_6', '7_7', '7_8'],
    },
    executionTime: 1.2,
    result: {
      status: 'route_updated',
      addedDistance: '120m',
      timeImpact: '+45 seconds',
    },
  },
  {
    id: 'log_14',
    timestamp: '10:24:35',
    type: 'reasoning',
    title: 'Mission Progress Analysis',
    content: 'Coverage at 67%. 12 survivors found of estimated 17. Remaining sectors include 3 smoke zones. Recommend increasing scan density in sectors 7_7 and 7_8.',
    metadata: {
      coverage: 67,
      survivorsFound: 12,
      survivorsEstimated: 17,
      remainingSectors: 33,
      priority: ['7_7', '7_8'],
    },
  },
  {
    id: 'log_15',
    timestamp: '10:24:40',
    type: 'tool_call',
    title: 'scan_sector',
    content: 'Deep thermal scan initiated on smoke zone 7_8 for remaining survivor detection.',
    droneId: 'drone_4',
    toolArgs: {
      drone_id: 'drone_4',
      sector_id: '7_8',
      scan_type: 'deep_thermal',
      sensitivity: 'high',
    },
    executionTime: 6.5,
    result: {
      survivors_found: 4,
      battery_remaining: 88.1,
      hazard_type: 'smoke',
      confidence: 0.89,
    },
  },
]

// Mock Agencies
export const agencies: Agency[] = [
  {
    id: 'bnpb',
    name: 'BNPB',
    country: 'Indonesia',
    countryCode: 'ID',
    connected: true,
    dataSharing: true,
    drones: 2,
  },
  {
    id: 'nadma',
    name: 'NADMA',
    country: 'Malaysia',
    countryCode: 'MY',
    connected: true,
    dataSharing: true,
    drones: 2,
  },
  {
    id: 'bfar',
    name: 'BFAR',
    country: 'Philippines',
    countryCode: 'PH',
    connected: false,
    dataSharing: false,
    drones: 1,
  },
]

// Mock Mission Presets
export const missionPresets: MissionPreset[] = [
  {
    id: 'preset_wildfire',
    name: 'Wildfire Peatland',
    disasterType: 'Fire',
    icon: 'Flame',
    config: {
      droneCount: 5,
      scanPattern: 'spiral',
      priorityZones: ['fire', 'smoke'],
      batteryThreshold: 20,
    },
  },
  {
    id: 'preset_flood',
    name: 'Flood Rescue',
    disasterType: 'Flood',
    icon: 'Waves',
    config: {
      droneCount: 4,
      scanPattern: 'grid',
      priorityZones: ['water', 'rooftops'],
      batteryThreshold: 25,
    },
  },
  {
    id: 'preset_earthquake',
    name: 'Earthquake Assessment',
    disasterType: 'Earthquake',
    icon: 'Mountain',
    config: {
      droneCount: 6,
      scanPattern: 'radial',
      priorityZones: ['collapsed', 'damaged'],
      batteryThreshold: 15,
    },
  },
  {
    id: 'preset_urban',
    name: 'Urban SAR',
    disasterType: 'Urban',
    icon: 'Building',
    config: {
      droneCount: 3,
      scanPattern: 'street',
      priorityZones: ['buildings', 'intersections'],
      batteryThreshold: 30,
    },
  },
  {
    id: 'preset_multi',
    name: 'Multi-Hazard',
    disasterType: 'Mixed',
    icon: 'AlertTriangle',
    config: {
      droneCount: 5,
      scanPattern: 'adaptive',
      priorityZones: ['all'],
      batteryThreshold: 20,
    },
  },
]

// Mock Bottlenecks
export const bottlenecks: Bottleneck[] = [
  {
    id: 'btn_1',
    severity: 'high',
    title: 'Single Point of Failure - Battery Management',
    description: 'drone_3 reached critical battery during active scan, causing 3% coverage loss. No backup drone was positioned nearby.',
    impact: 85,
    recommendation: 'Implement predictive battery rotation with 25% threshold trigger',
    affectedDrones: ['drone_3'],
  },
  {
    id: 'btn_2',
    severity: 'medium',
    title: 'No-Fly Zone Rerouting Delay',
    description: 'drone_4 lost 45 seconds to reroute around sector 6_6. Pre-mission no-fly zone mapping could prevent this.',
    impact: 55,
    recommendation: 'Integrate real-time airspace restriction API into pre-flight planning',
    affectedDrones: ['drone_4'],
  },
  {
    id: 'btn_3',
    severity: 'low',
    title: 'Scan Density Variance',
    description: 'Thermal scan confidence varied from 0.89 to 0.94 across sectors. Consistent calibration needed.',
    impact: 25,
    recommendation: 'Run calibration routine before each mission start',
    affectedDrones: ['drone_1', 'drone_2', 'drone_4'],
  },
]

// Mock Recommendations
export const recommendations: Recommendation[] = [
  {
    id: 'rec_1',
    rank: 1,
    impact: 'high',
    title: 'Implement Predictive Battery Rotation',
    description: 'Add 25% battery threshold triggers with automated backup drone deployment to prevent coverage gaps.',
  },
  {
    id: 'rec_2',
    rank: 2,
    impact: 'high',
    title: 'Pre-Flight Airspace Integration',
    description: 'Connect to national airspace restriction APIs to pre-compute no-fly zones before mission start.',
  },
  {
    id: 'rec_3',
    rank: 3,
    impact: 'medium',
    title: 'Add Sixth Drone to Fleet',
    description: 'Current 5-drone fleet has 0% redundancy. Adding one drone provides hot-swap capability.',
  },
  {
    id: 'rec_4',
    rank: 4,
    impact: 'medium',
    title: 'Thermal Sensor Calibration Protocol',
    description: 'Implement pre-mission calibration routine to ensure consistent 0.92+ confidence across all units.',
  },
  {
    id: 'rec_5',
    rank: 5,
    impact: 'low',
    title: 'Optimize Scan Pattern for Fire Zones',
    description: 'Switch from grid to spiral pattern in fire zones to reduce exposure time and improve survivor detection.',
  },
]

// Performance metrics for charts
export const coverageOverTime = [
  { time: '0:00', coverage: 0 },
  { time: '2:00', coverage: 12 },
  { time: '4:00', coverage: 28 },
  { time: '6:00', coverage: 41 },
  { time: '8:00', coverage: 52 },
  { time: '10:00', coverage: 67 },
  { time: '12:00', coverage: 78 },
  { time: '14:00', coverage: 89 },
  { time: '16:00', coverage: 95 },
  { time: '18:00', coverage: 100 },
]

export const batteryDepletion = [
  { time: '0:00', drone_1: 100, drone_2: 100, drone_3: 100, drone_4: 100, drone_5: 65 },
  { time: '3:00', drone_1: 95, drone_2: 94, drone_3: 92, drone_4: 98, drone_5: 58 },
  { time: '6:00', drone_1: 91, drone_2: 85, drone_3: 65, drone_4: 96, drone_5: 52 },
  { time: '9:00', drone_1: 87, drone_2: 72, drone_3: 35, drone_4: 95, drone_5: 45 },
  { time: '12:00', drone_1: 87, drone_2: 72, drone_3: 18, drone_4: 95, drone_5: 45 },
]

export const survivorTimeline = [
  { time: 2, count: 2, hazard: 'fire', sector: '2_3' },
  { time: 5, count: 3, hazard: 'fire', sector: '4_5' },
  { time: 7, count: 1, hazard: 'smoke', sector: '3_3' },
  { time: 9, count: 2, hazard: 'smoke', sector: '5_5' },
  { time: 11, count: 4, hazard: 'smoke', sector: '7_8' },
]

// MCP Tools for configuration
export const mcpTools = [
  { id: 'scan_sector', name: 'scan_sector', enabled: true, calls: 45 },
  { id: 'move_to', name: 'move_to', enabled: true, calls: 89 },
  { id: 'recall_drone', name: 'recall_drone', enabled: true, calls: 3 },
  { id: 'update_route', name: 'update_route', enabled: true, calls: 12 },
  { id: 'dispatch_extraction', name: 'dispatch_extraction', enabled: true, calls: 7 },
  { id: 'calibrate_sensor', name: 'calibrate_sensor', enabled: false, calls: 0 },
]
