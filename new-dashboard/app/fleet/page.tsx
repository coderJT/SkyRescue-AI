'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/app-shell'
import { SectionLabel } from '@/components/ui/section-label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  RefreshCw,
  Save,
  RotateCcw,
  Flame,
  Droplets,
  Mountain,
  Building,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  Clock,
  Settings,
  Key,
  Bell,
  Database,
  Lock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  drones,
  agencies,
  missionPresets,
  mcpTools,
  type Drone,
} from '@/lib/mock-data'

const presetIcons: Record<string, typeof Flame> = {
  Flame: Flame,
  Waves: Droplets,
  Mountain: Mountain,
  Building: Building,
  AlertTriangle: AlertTriangle,
}

function DroneDetailsDialog({ drone }: { drone: Drone }) {
  return (
    <DialogContent className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <span className="font-mono text-primary">{drone.id}</span>
          <Badge variant="outline">{drone.type}</Badge>
        </DialogTitle>
        <DialogDescription>Drone details and configuration</DialogDescription>
      </DialogHeader>
      <div className="space-y-4 py-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-muted-foreground">Name</Label>
            <p className="font-medium">{drone.name}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Type</Label>
            <p className="font-medium">{drone.type}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Owner Agency</Label>
            <p className="font-medium">{drone.ownerAgency}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Status</Label>
            <Badge
              className={cn(
                'capitalize',
                drone.status === 'active' && 'bg-success/10 text-success',
                drone.status === 'charging' && 'bg-muted text-muted-foreground',
                drone.status === 'offline' && 'bg-error/10 text-error'
              )}
            >
              {drone.status}
            </Badge>
          </div>
        </div>
        <div>
          <Label className="text-muted-foreground">Battery Health</Label>
          <div className="mt-2 flex items-center gap-3">
            <Progress value={drone.battery} className="h-2 flex-1" />
            <span className="font-mono text-sm">{drone.battery}%</span>
          </div>
        </div>
        <div>
          <Label className="text-muted-foreground">Current Coordinates</Label>
          <p className="font-mono text-sm">
            X: {drone.coordinates.x.toFixed(1)}, Y: {drone.coordinates.y.toFixed(1)}, Z: {drone.coordinates.z.toFixed(1)}
          </p>
        </div>
        <div>
          <Label className="text-muted-foreground">Target Sector</Label>
          <p className="font-mono">{drone.targetSector}</p>
        </div>
        <div>
          <Label className="text-muted-foreground">Last Seen</Label>
          <p className="text-sm">{drone.lastSeen}</p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline">Edit Drone</Button>
        <Button variant="destructive">Remove Drone</Button>
      </DialogFooter>
    </DialogContent>
  )
}

function AgencyCard({ agency }: { agency: typeof agencies[0] }) {
  const [dataSharing, setDataSharing] = useState(agency.dataSharing)

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-2xl">
              {agency.countryCode === 'ID' && '🇮🇩'}
              {agency.countryCode === 'MY' && '🇲🇾'}
              {agency.countryCode === 'PH' && '🇵🇭'}
            </div>
            <div>
              <h4 className="font-semibold text-primary">{agency.name}</h4>
              <p className="text-sm text-muted-foreground">{agency.country}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'flex h-3 w-3 rounded-full',
                agency.connected ? 'bg-success' : 'bg-error'
              )}
            />
            <span className="text-sm text-muted-foreground">
              {agency.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-border pt-4">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Data Sharing</span>
          </div>
          <Switch
            checked={dataSharing}
            onCheckedChange={setDataSharing}
            className="data-[state=checked]:bg-primary"
          />
        </div>
        <div className="mt-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Drones: {agency.drones}</span>
          <Button variant="ghost" size="sm" className="text-primary">
            View Details
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function PresetCard({ preset }: { preset: typeof missionPresets[0] }) {
  const Icon = presetIcons[preset.icon] || AlertTriangle

  return (
    <Card className="transition-all hover:shadow-lg">
      <CardContent className="p-5">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg gradient-orange">
            <Icon className="h-6 w-6 text-white" />
          </div>
          <Badge variant="outline" className="text-primary">
            {preset.disasterType}
          </Badge>
        </div>
        <h4 className="mb-2 font-semibold text-foreground">{preset.name}</h4>
        <div className="mb-4 space-y-1 text-sm text-muted-foreground">
          <p>Drones: {preset.config.droneCount}</p>
          <p>Pattern: {preset.config.scanPattern}</p>
          <p>Battery Threshold: {preset.config.batteryThreshold}%</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" className="flex-1 gradient-orange text-white hover:brightness-110">
            Load
          </Button>
          <Button size="sm" variant="outline">
            <Edit2 className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" className="text-destructive hover:bg-destructive/10">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default function FleetHubPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [toolStates, setToolStates] = useState<Record<string, boolean>>(
    Object.fromEntries(mcpTools.map((t) => [t.id, t.enabled]))
  )
  const [retentionDays, setRetentionDays] = useState([30])
  const [federatedLearning, setFederatedLearning] = useState(true)
  const [notifications, setNotifications] = useState({
    critical: true,
    warnings: true,
    info: false,
    missionComplete: true,
  })

  const filteredDrones = drones.filter(
    (drone) =>
      drone.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      drone.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      drone.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      drone.ownerAgency.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const toggleTool = (toolId: string) => {
    setToolStates((prev) => ({ ...prev, [toolId]: !prev[toolId] }))
  }

  return (
    <AppShell title="Fleet Hub">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header Section */}
        <div className="mb-8">
          <SectionLabel>Configuration</SectionLabel>
          <h1 className="mt-4 font-serif text-4xl tracking-tight text-foreground lg:text-5xl">
            Agency & <span className="gradient-text">Fleet</span> Hub
          </h1>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="fleet" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:grid-cols-none lg:flex">
            <TabsTrigger value="fleet">Fleet Registry</TabsTrigger>
            <TabsTrigger value="agencies">Agencies</TabsTrigger>
            <TabsTrigger value="mcp">MCP Config</TabsTrigger>
            <TabsTrigger value="presets">Presets</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Fleet Registry Tab */}
          <TabsContent value="fleet">
            <Card>
              <CardHeader>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle>Fleet Registry</CardTitle>
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="Search drones..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-64 pl-9"
                      />
                    </div>
                    <Button className="gap-2 gradient-orange text-white shadow-accent hover:brightness-110">
                      <Plus className="h-4 w-4" />
                      Add Drone
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-primary">Drone ID</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Battery</TableHead>
                        <TableHead>Owner Agency</TableHead>
                        <TableHead>Last Seen</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredDrones.map((drone) => (
                        <TableRow key={drone.id} className="cursor-pointer hover:bg-muted/50">
                          <TableCell className="font-mono font-semibold text-primary">
                            {drone.id}
                          </TableCell>
                          <TableCell>{drone.type}</TableCell>
                          <TableCell>
                            <Badge
                              className={cn(
                                'capitalize',
                                drone.status === 'active' && 'bg-success/10 text-success border-success/20',
                                drone.status === 'scanning' && 'bg-info/10 text-info border-info/20',
                                drone.status === 'returning' && 'bg-warning/10 text-warning border-warning/20',
                                drone.status === 'charging' && 'bg-muted text-muted-foreground',
                                drone.status === 'offline' && 'bg-error/10 text-error border-error/20'
                              )}
                            >
                              {drone.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={drone.battery} className="h-2 w-20" />
                              <span
                                className={cn(
                                  'font-mono text-xs',
                                  drone.battery > 50 && 'text-success',
                                  drone.battery <= 50 && drone.battery > 25 && 'text-warning',
                                  drone.battery <= 25 && 'text-error'
                                )}
                              >
                                {drone.battery}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{drone.ownerAgency}</Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">{drone.lastSeen}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Dialog>
                                <DialogTrigger asChild>
                                  <Button variant="ghost" size="icon">
                                    <Edit2 className="h-4 w-4" />
                                  </Button>
                                </DialogTrigger>
                                <DroneDetailsDialog drone={drone} />
                              </Dialog>
                              <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Agencies Tab */}
          <TabsContent value="agencies">
            <div className="space-y-6">
              {/* Agency Network Map Placeholder */}
              <Card>
                <CardHeader>
                  <CardTitle>Agency Network Map</CardTitle>
                  <CardDescription>Visual representation of connected agencies</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
                    <div className="text-center">
                      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl gradient-orange shadow-accent">
                        <Activity className="h-8 w-8 text-white" />
                      </div>
                      <p className="text-lg font-medium text-foreground">Network Visualization</p>
                      <p className="text-sm text-muted-foreground">Agency connection graph renders here</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Agency Cards */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {agencies.map((agency) => (
                  <AgencyCard key={agency.id} agency={agency} />
                ))}
              </div>
            </div>
          </TabsContent>

          {/* MCP Config Tab */}
          <TabsContent value="mcp">
            <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
              {/* Server Health */}
              <div className="rounded-xl bg-gradient-to-br from-primary via-accent-secondary to-primary p-[2px]">
                <Card className="h-full rounded-[calc(12px-2px)] border-0">
                  <CardHeader>
                    <CardTitle>Server Health</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="flex items-center gap-4">
                      <div className="relative flex h-16 w-16 items-center justify-center">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-25" />
                        <span className="relative flex h-10 w-10 items-center justify-center rounded-full bg-success">
                          <CheckCircle className="h-6 w-6 text-white" />
                        </span>
                      </div>
                      <div>
                        <p className="text-2xl font-semibold text-success">Connected</p>
                        <p className="text-sm text-muted-foreground">MCP Server Online</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-lg bg-muted p-3">
                        <p className="text-sm text-muted-foreground">Latency</p>
                        <p className="text-xl font-semibold text-success">23ms</p>
                      </div>
                      <div className="rounded-lg bg-muted p-3">
                        <p className="text-sm text-muted-foreground">Active Tools</p>
                        <p className="text-xl font-semibold text-foreground">
                          {Object.values(toolStates).filter(Boolean).length}
                        </p>
                      </div>
                    </div>
                    <Button variant="outline" className="w-full gap-2 border-primary text-primary hover:bg-primary/10">
                      <RefreshCw className="h-4 w-4" />
                      Restart Server
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Tool Registry */}
              <Card>
                <CardHeader>
                  <CardTitle>Tool Registry</CardTitle>
                  <CardDescription>Enable or disable MCP tools</CardDescription>
                </CardHeader>
                <CardContent>
                  <Accordion type="single" collapsible className="w-full">
                    {mcpTools.map((tool) => (
                      <AccordionItem key={tool.id} value={tool.id}>
                        <AccordionTrigger className="hover:no-underline">
                          <div className="flex items-center gap-3">
                            <Switch
                              checked={toolStates[tool.id]}
                              onCheckedChange={() => toggleTool(tool.id)}
                              onClick={(e) => e.stopPropagation()}
                              className="data-[state=checked]:bg-primary"
                            />
                            <span className="font-mono text-sm">{tool.name}</span>
                            <Badge variant="outline" className="text-xs">
                              {tool.calls} calls
                            </Badge>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="rounded-lg bg-muted p-4">
                            <p className="text-sm text-muted-foreground">
                              Tool documentation and configuration options would appear here.
                            </p>
                            <div className="mt-3 flex gap-2">
                              <Button size="sm" variant="outline">
                                View Logs
                              </Button>
                              <Button size="sm" variant="outline">
                                Configure
                              </Button>
                            </div>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Presets Tab */}
          <TabsContent value="presets">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {missionPresets.map((preset) => (
                <PresetCard key={preset.id} preset={preset} />
              ))}
              
              {/* Create New Preset Card */}
              <Card className="flex min-h-[280px] cursor-pointer items-center justify-center border-2 border-dashed border-border transition-all hover:border-primary/50 hover:bg-muted/50">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground">
                    <Plus className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="font-medium text-muted-foreground">Create New Preset</p>
                </div>
              </Card>
            </div>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* LLM Configuration */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Settings className="h-5 w-5 text-primary" />
                    <CardTitle>LLM Configuration</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Select defaultValue="gpt-4">
                      <SelectTrigger>
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gpt-4">GPT-4 Turbo</SelectItem>
                        <SelectItem value="gpt-3.5">GPT-3.5 Turbo</SelectItem>
                        <SelectItem value="claude-3">Claude 3 Opus</SelectItem>
                        <SelectItem value="llama-3">Llama 3 70B</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>API Key</Label>
                    <div className="relative">
                      <Key className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        type="password"
                        placeholder="sk-..."
                        className="pl-9"
                        defaultValue="sk-xxxxxxxxxxxxxxxxxxxxx"
                      />
                    </div>
                  </div>
                  <Button variant="outline" className="w-full gap-2">
                    <Activity className="h-4 w-4" />
                    Test Connection
                  </Button>
                </CardContent>
              </Card>

              {/* Data & Privacy */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Lock className="h-5 w-5 text-primary" />
                    <CardTitle>Data & Privacy</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <Label>Data Retention: {retentionDays[0]} days</Label>
                    </div>
                    <Slider
                      value={retentionDays}
                      onValueChange={setRetentionDays}
                      min={7}
                      max={90}
                      step={1}
                      className="[&_[role=slider]]:bg-primary"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Federated Learning</Label>
                      <p className="text-sm text-muted-foreground">Share anonymized insights across agencies</p>
                    </div>
                    <Switch
                      checked={federatedLearning}
                      onCheckedChange={setFederatedLearning}
                      className="data-[state=checked]:bg-primary"
                    />
                  </div>
                  <Button variant="outline" className="w-full gap-2">
                    <Database className="h-4 w-4" />
                    Export All Data
                  </Button>
                </CardContent>
              </Card>

              {/* Notifications */}
              <Card className="lg:col-span-2">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Bell className="h-5 w-5 text-primary" />
                    <CardTitle>Notifications</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="flex items-center justify-between rounded-lg border border-border p-4">
                      <div>
                        <Label>Critical Alerts</Label>
                        <p className="text-sm text-muted-foreground">Survivor detection, hazards</p>
                      </div>
                      <Switch
                        checked={notifications.critical}
                        onCheckedChange={(v) => setNotifications({ ...notifications, critical: v })}
                        className="data-[state=checked]:bg-primary"
                      />
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-border p-4">
                      <div>
                        <Label>Warnings</Label>
                        <p className="text-sm text-muted-foreground">Low battery, route changes</p>
                      </div>
                      <Switch
                        checked={notifications.warnings}
                        onCheckedChange={(v) => setNotifications({ ...notifications, warnings: v })}
                        className="data-[state=checked]:bg-primary"
                      />
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-border p-4">
                      <div>
                        <Label>Info Messages</Label>
                        <p className="text-sm text-muted-foreground">Scan updates, progress</p>
                      </div>
                      <Switch
                        checked={notifications.info}
                        onCheckedChange={(v) => setNotifications({ ...notifications, info: v })}
                        className="data-[state=checked]:bg-primary"
                      />
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-border p-4">
                      <div>
                        <Label>Mission Complete</Label>
                        <p className="text-sm text-muted-foreground">Full coverage achieved</p>
                      </div>
                      <Switch
                        checked={notifications.missionComplete}
                        onCheckedChange={(v) => setNotifications({ ...notifications, missionComplete: v })}
                        className="data-[state=checked]:bg-primary"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Sticky Footer Actions */}
        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">
            <Clock className="mr-1 inline h-4 w-4" />
            Last saved: 2 minutes ago
          </p>
          <div className="flex gap-3">
            <Button variant="outline" className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Reset to Defaults
            </Button>
            <Button className="gap-2 gradient-orange text-white shadow-accent hover:brightness-110">
              <Save className="h-4 w-4" />
              Save Configuration
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
