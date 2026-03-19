'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/app-shell'
import { SectionLabel } from '@/components/ui/section-label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  BarChart3,
  Users,
  Clock,
  Battery,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Download,
  CheckCircle,
  XCircle,
  ChevronRight,
  Plus,
  Zap,
  Shield,
  Award,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
} from 'recharts'
import {
  coverageOverTime,
  batteryDepletion,
  survivorTimeline,
  bottlenecks,
  recommendations,
  gridSectors,
} from '@/lib/mock-data'

// A/B Test Timeline Data
const abTestTimeline = [
  { time: '0:00', baseline: 0, aggressive: 0, conservative: 0 },
  { time: '2:00', baseline: 15, aggressive: 22, conservative: 10 },
  { time: '4:00', baseline: 32, aggressive: 45, conservative: 25 },
  { time: '6:00', baseline: 48, aggressive: 65, conservative: 38 },
  { time: '8:00', baseline: 62, aggressive: 78, conservative: 50 },
  { time: '10:00', baseline: 75, aggressive: 88, conservative: 62 },
  { time: '12:00', baseline: 85, aggressive: 95, conservative: 72 },
  { time: '14:00', baseline: 92, aggressive: 100, conservative: 82 },
  { time: '16:00', baseline: 97, aggressive: 100, conservative: 90 },
  { time: '18:00', baseline: 100, aggressive: 100, conservative: 96 },
]

// KPI Card with Sparkline
function KPICard({
  icon,
  label,
  value,
  trend,
  trendDirection,
  sparklineData,
}: {
  icon: React.ReactNode
  label: string
  value: string
  trend: string
  trendDirection: 'up' | 'down' | 'neutral'
  sparklineData: number[]
}) {
  return (
    <Card className="relative overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
          <div
            className={cn(
              'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
              trendDirection === 'up' && 'bg-success/10 text-success',
              trendDirection === 'down' && 'bg-error/10 text-error',
              trendDirection === 'neutral' && 'bg-muted text-muted-foreground'
            )}
          >
            {trendDirection === 'up' && <TrendingUp className="h-3 w-3" />}
            {trendDirection === 'down' && <TrendingDown className="h-3 w-3" />}
            {trend}
          </div>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-semibold tracking-tight text-foreground">{value}</p>
          <p className="mt-1 text-sm text-muted-foreground">{label}</p>
        </div>
        {/* Mini Sparkline */}
        <div className="mt-4 h-12">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData.map((v, i) => ({ value: v, index: i }))}>
              <defs>
                <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FF6B00" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#FF6B00" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="value"
                stroke="#FF6B00"
                strokeWidth={2}
                fill="url(#sparklineGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Metric Comparison Component for A/B Testing
function MetricComparison({ 
  label, 
  baseline, 
  testValue, 
  improvement, 
  direction 
}: {
  label: string
  baseline: string
  testValue: string
  improvement: string
  direction: 'better' | 'worse'
}) {
  const isBetter = direction === 'better'
  
  return (
    <div className="flex items-center justify-between rounded-lg border border-border/40 p-2.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground line-through">{baseline}</span>
        <span className="text-sm font-semibold">{testValue}</span>
        <Badge 
          variant="outline" 
          className={cn(
            'text-xs',
            isBetter 
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300' 
              : 'bg-red-50 text-red-700 border-red-300'
          )}
        >
          {improvement}
        </Badge>
      </div>
    </div>
  )
}

// Bottleneck Card
function BottleneckCard({
  bottleneck,
}: {
  bottleneck: typeof bottlenecks[0]
}) {
  const severityConfig = {
    high: { color: 'bg-error/10 text-error border-error/20' },
    medium: { color: 'bg-warning/10 text-warning border-warning/20' },
    low: { color: 'bg-success/10 text-success border-success/20' },
  }

  const config = severityConfig[bottleneck.severity]

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-3 flex items-start justify-between">
          <Badge className={cn('capitalize', config.color)}>
            {bottleneck.severity}
          </Badge>
          <div className="flex gap-1">
            {bottleneck.affectedDrones.map((drone) => (
              <Badge key={drone} variant="outline" className="font-mono text-xs">
                {drone}
              </Badge>
            ))}
          </div>
        </div>
        <h4 className="mb-2 font-semibold text-foreground">{bottleneck.title}</h4>
        <p className="mb-4 text-sm text-muted-foreground">{bottleneck.description}</p>
        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Impact Score</span>
            <span className="font-semibold text-primary">{bottleneck.impact}%</span>
          </div>
          <Progress value={bottleneck.impact} className="h-2" />
        </div>
        <Button variant="link" className="h-auto p-0 text-sm text-primary">
          {bottleneck.recommendation}
          <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  )
}

// Recommendation Card
function RecommendationCard({
  recommendation,
  onApply,
  onDismiss,
}: {
  recommendation: typeof recommendations[0]
  onApply: () => void
  onDismiss: () => void
}) {
  const impactConfig = {
    high: 'bg-primary/10 text-primary border-primary/20',
    medium: 'bg-warning/10 text-warning border-warning/20',
    low: 'bg-muted text-muted-foreground border-border',
  }

  return (
    <div className="flex items-start gap-4 rounded-lg border border-border p-4 transition-all hover:shadow-md">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full gradient-orange text-sm font-bold text-white">
        {recommendation.rank}
      </div>
      <div className="flex-1">
        <div className="mb-2 flex items-center gap-2">
          <Badge className={cn('capitalize', impactConfig[recommendation.impact])}>
            {recommendation.impact} Impact
          </Badge>
        </div>
        <h4 className="mb-1 font-semibold text-foreground">{recommendation.title}</h4>
        <p className="mb-3 text-sm text-muted-foreground">{recommendation.description}</p>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="gap-1 border-primary text-primary hover:bg-primary/10" onClick={onApply}>
            <CheckCircle className="h-3.5 w-3.5" />
            Apply
          </Button>
          <Button size="sm" variant="ghost" className="gap-1 text-muted-foreground" onClick={onDismiss}>
            <XCircle className="h-3.5 w-3.5" />
            Dismiss
          </Button>
        </div>
      </div>
    </div>
  )
}

// Hazard Heatmap
function HazardHeatmap() {
  return (
    <div className="grid grid-cols-10 gap-1">
      {gridSectors.map((sector) => {
        let intensity = 0
        if (sector.hazard === 'fire') intensity = 100
        else if (sector.hazard === 'smoke') intensity = 60
        else if (sector.scanned) intensity = 20
        
        return (
          <div
            key={sector.id}
            className="aspect-square rounded-sm transition-all hover:scale-110"
            style={{
              backgroundColor: intensity > 0 
                ? `rgba(255, 107, 0, ${intensity / 100})`
                : '#F1F5F9',
            }}
            title={`Sector ${sector.id} - ${sector.hazard} (${intensity}% intensity)`}
          />
        )
      })}
    </div>
  )
}

export default function PerformancePage() {
  const [comparisonMode, setComparisonMode] = useState<'single' | 'compare'>('single')

  return (
    <AppShell title="Performance">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header Section */}
        <div className="mb-8">
          <SectionLabel>Performance</SectionLabel>
          <h1 className="mt-4 font-serif text-4xl tracking-tight text-foreground lg:text-5xl">
            <span className="gradient-text">Performance</span> & Optimization
          </h1>
          
          {/* Controls */}
          <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <Tabs value={comparisonMode} onValueChange={(v) => setComparisonMode(v as 'single' | 'compare')}>
              <TabsList>
                <TabsTrigger value="single">Single Mission</TabsTrigger>
                <TabsTrigger value="compare">Compare Missions</TabsTrigger>
              </TabsList>
            </Tabs>
            <Button variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Export Report
            </Button>
          </div>
        </div>

        {/* KPI Cards Row */}
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            icon={<BarChart3 className="h-5 w-5" />}
            label="Coverage Efficiency"
            value="92%"
            trend="+12%"
            trendDirection="up"
            sparklineData={[45, 52, 61, 73, 85, 92]}
          />
          <KPICard
            icon={<Users className="h-5 w-5" />}
            label="Survivor Detection"
            value="100%"
            trend="Perfect"
            trendDirection="up"
            sparklineData={[60, 75, 85, 95, 100, 100]}
          />
          <KPICard
            icon={<Clock className="h-5 w-5" />}
            label="Avg Response Time"
            value="3.2 min"
            trend="-18%"
            trendDirection="up"
            sparklineData={[5.2, 4.8, 4.1, 3.8, 3.5, 3.2]}
          />
          <KPICard
            icon={<Battery className="h-5 w-5" />}
            label="Battery Efficiency"
            value="78%"
            trend="+5%"
            trendDirection="up"
            sparklineData={[65, 68, 71, 74, 76, 78]}
          />
        </div>

        {/* A/B Testing Section */}
        <section className="mb-8 space-y-6">
          {/* Section Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SectionLabel pulse={false}>A/B Testing</SectionLabel>
              <h2 className="text-2xl font-serif font-semibold text-foreground">Strategy Comparison</h2>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Test
              </Button>
              <Button variant="outline" size="sm">
                Export Results
              </Button>
            </div>
          </div>

          {/* A/B Test Cards Grid */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Test Card 1 - Aggressive Strategy */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4">
                <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300">
                  Test A
                </Badge>
              </div>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Zap className="h-5 w-5 text-amber-500" />
                  Aggressive Strategy
                </CardTitle>
                <CardDescription className="text-xs">
                  Prioritize speed over battery efficiency
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <MetricComparison 
                    label="Coverage Time"
                    baseline="18.5 min"
                    testValue="14.2 min"
                    improvement="-23%"
                    direction="better"
                  />
                  <MetricComparison 
                    label="Battery Usage"
                    baseline="78%"
                    testValue="94%"
                    improvement="+21%"
                    direction="worse"
                  />
                  <MetricComparison 
                    label="Survivors Found"
                    baseline="15/17"
                    testValue="17/17"
                    improvement="+13%"
                    direction="better"
                  />
                  <MetricComparison 
                    label="Avg Response Time"
                    baseline="4.8 min"
                    testValue="3.1 min"
                    improvement="-35%"
                    direction="better"
                  />
                </div>
                
                <div className="rounded-lg bg-amber-50 p-3 text-center">
                  <p className="text-sm font-semibold text-amber-900">
                    3/4 Metrics Improved
                  </p>
                  <p className="text-xs text-amber-700">
                    Faster coverage, higher battery cost
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Test Card 2 - Conservative Strategy */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4">
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
                  Test B
                </Badge>
              </div>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Shield className="h-5 w-5 text-blue-500" />
                  Conservative Strategy
                </CardTitle>
                <CardDescription className="text-xs">
                  Prioritize battery safety and reliability
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <MetricComparison 
                    label="Coverage Time"
                    baseline="18.5 min"
                    testValue="24.7 min"
                    improvement="+34%"
                    direction="worse"
                  />
                  <MetricComparison 
                    label="Battery Usage"
                    baseline="78%"
                    testValue="62%"
                    improvement="-21%"
                    direction="better"
                  />
                  <MetricComparison 
                    label="Survivors Found"
                    baseline="15/17"
                    testValue="16/17"
                    improvement="+7%"
                    direction="better"
                  />
                  <MetricComparison 
                    label="Avg Response Time"
                    baseline="4.8 min"
                    testValue="6.2 min"
                    improvement="+29%"
                    direction="worse"
                  />
                </div>
                
                <div className="rounded-lg bg-blue-50 p-3 text-center">
                  <p className="text-sm font-semibold text-blue-900">
                    2/4 Metrics Improved
                  </p>
                  <p className="text-xs text-blue-700">
                    Better battery, slower coverage
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Test Card 3 - Current/Baseline */}
            <Card className="relative overflow-hidden ring-2 ring-primary">
              <div className="absolute top-0 right-0 p-4">
                <Badge className="bg-primary text-white">
                  Current
                </Badge>
              </div>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Award className="h-5 w-5 text-primary" />
                  Balanced Strategy
                </CardTitle>
                <CardDescription className="text-xs">
                  Current production configuration
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm rounded-lg border border-border/40 p-2.5">
                    <span className="text-muted-foreground">Coverage Time</span>
                    <span className="font-semibold">18.5 min</span>
                  </div>
                  <div className="flex justify-between text-sm rounded-lg border border-border/40 p-2.5">
                    <span className="text-muted-foreground">Battery Usage</span>
                    <span className="font-semibold">78%</span>
                  </div>
                  <div className="flex justify-between text-sm rounded-lg border border-border/40 p-2.5">
                    <span className="text-muted-foreground">Survivors Found</span>
                    <span className="font-semibold">15/17</span>
                  </div>
                  <div className="flex justify-between text-sm rounded-lg border border-border/40 p-2.5">
                    <span className="text-muted-foreground">Response Time</span>
                    <span className="font-semibold">4.8 min</span>
                  </div>
                </div>
                
                <div className="rounded-lg bg-primary/5 p-3 text-center">
                  <p className="text-sm font-semibold text-primary">
                    Baseline Configuration
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Recommended for production
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Comparison Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Timeline Comparison</CardTitle>
              <CardDescription>
                Side-by-side visualization of all test strategies over mission duration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={abTestTimeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="time" stroke="#64748B" fontSize={12} />
                    <YAxis stroke="#64748B" fontSize={12} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="baseline" 
                      stroke="#FF6B00" 
                      strokeWidth={3}
                      name="Balanced (Current)"
                      dot={false}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="aggressive" 
                      stroke="#F59E0B" 
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      name="Aggressive"
                      dot={false}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="conservative" 
                      stroke="#3B82F6" 
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      name="Conservative"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Statistical Significance */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-1">Confidence Level</p>
                  <p className="text-3xl font-bold text-primary">94.2%</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Results are statistically significant
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-1">Sample Size</p>
                  <p className="text-3xl font-bold text-foreground">127</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Missions analyzed
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-1">Recommended Action</p>
                  <p className="text-lg font-semibold text-amber-600">Test Aggressive</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    For time-critical missions
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Charts Section */}
        <div className="mb-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          {/* Coverage Over Time */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Coverage Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={coverageOverTime}>
                    <defs>
                      <linearGradient id="coverageGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#FF6B00" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#FF6B00" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#64748B" />
                    <YAxis tick={{ fontSize: 12 }} stroke="#64748B" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="coverage"
                      stroke="#94A3B8"
                      strokeDasharray="5 5"
                      strokeWidth={1}
                      dot={false}
                      name="Target (100%)"
                    />
                    <Area
                      type="monotone"
                      dataKey="coverage"
                      stroke="#FF6B00"
                      strokeWidth={3}
                      fill="url(#coverageGradient)"
                      name="Coverage %"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Battery Depletion */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Battery Depletion</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={batteryDepletion}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#64748B" />
                    <YAxis tick={{ fontSize: 12 }} stroke="#64748B" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="drone_1" stroke="#FF6B00" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="drone_2" stroke="#FF9E4D" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="drone_3" stroke="#EF4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="drone_4" stroke="#3B82F6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="drone_5" stroke="#10B981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Row 2: Survivor Timeline & Hazard Heatmap */}
        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          {/* Survivor Detection Timeline */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Survivor Detection Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="time" type="number" name="Time (min)" tick={{ fontSize: 12 }} stroke="#64748B" />
                    <YAxis dataKey="count" name="Survivors" tick={{ fontSize: 12 }} stroke="#64748B" />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px',
                      }}
                    />
                    <Scatter name="Survivors" data={survivorTimeline}>
                      {survivorTimeline.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.hazard === 'fire' ? '#EF4444' : '#F59E0B'}
                        />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 flex items-center justify-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-error" />
                  <span className="text-sm text-muted-foreground">Fire Zone</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-warning" />
                  <span className="text-sm text-muted-foreground">Smoke Zone</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Hazard Exposure Heatmap */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Hazard Exposure Heatmap</CardTitle>
            </CardHeader>
            <CardContent>
              <HazardHeatmap />
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Low</span>
                <div className="flex h-3 w-48 rounded-full overflow-hidden">
                  <div className="flex-1 bg-muted" />
                  <div className="flex-1" style={{ backgroundColor: 'rgba(255, 107, 0, 0.3)' }} />
                  <div className="flex-1" style={{ backgroundColor: 'rgba(255, 107, 0, 0.6)' }} />
                  <div className="flex-1" style={{ backgroundColor: 'rgba(255, 107, 0, 1)' }} />
                </div>
                <span className="text-muted-foreground">High</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Bottleneck Analysis */}
        <div className="mb-8">
          <SectionLabel pulse={false}>Bottlenecks</SectionLabel>
          <h2 className="mt-4 mb-6 font-serif text-2xl text-foreground">Bottleneck Analysis</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {bottlenecks.map((bottleneck) => (
              <BottleneckCard key={bottleneck.id} bottleneck={bottleneck} />
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="mb-8">
          <SectionLabel pulse={false}>Recommendations</SectionLabel>
          <h2 className="mt-4 mb-6 font-serif text-2xl text-foreground">Optimization Recommendations</h2>
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <RecommendationCard
                key={rec.id}
                recommendation={rec}
                onApply={() => {}}
                onDismiss={() => {}}
              />
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
