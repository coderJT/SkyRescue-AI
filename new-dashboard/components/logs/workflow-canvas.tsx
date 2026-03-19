'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Zap,
  Brain,
  Terminal,
  GitBranch,
  CheckCircle,
  AlertTriangle,
  X,
  Copy,
  Clock,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Move,
} from 'lucide-react'
import type { AgentLogEntry, LogType } from '@/lib/mock-data'

interface WorkflowNode {
  id: string
  type: LogType
  title: string
  timestamp: string
  content: string
  droneId?: string
  executionTime?: number
  toolArgs?: Record<string, unknown>
  result?: Record<string, unknown>
  metadata?: Record<string, unknown>
  position: { x: number; y: number }
}

interface WorkflowCanvasProps {
  entries: AgentLogEntry[]
  onNodeSelect?: (node: WorkflowNode | null) => void
  selectedNodeId?: string | null
  zoom: number
  onZoomChange: (zoom: number) => void
}

const nodeConfig: Record<LogType, { icon: typeof Zap; color: string; bgColor: string; borderColor: string }> = {
  trigger: {
    icon: Zap,
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
  },
  reasoning: {
    icon: Brain,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  tool_call: {
    icon: Terminal,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  condition: {
    icon: GitBranch,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  result: {
    icon: CheckCircle,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
}

function generateNodePositions(entries: AgentLogEntry[]): WorkflowNode[] {
  const nodeWidth = 280
  const nodeHeight = 120
  const horizontalGap = 120
  const verticalGap = 60
  const nodesPerRow = 3
  
  return entries.map((entry, index) => {
    const row = Math.floor(index / nodesPerRow)
    const col = index % nodesPerRow
    
    // Add some variation to make it look more organic
    const xOffset = (row % 2 === 1 ? 60 : 0) + (Math.sin(index) * 15)
    const yOffset = Math.cos(index) * 10
    
    return {
      ...entry,
      position: {
        x: col * (nodeWidth + horizontalGap) + 80 + xOffset,
        y: row * (nodeHeight + verticalGap) + 80 + yOffset,
      },
    }
  })
}

function ConnectionLine({ 
  from, 
  to, 
  isHighlighted,
  zoom
}: { 
  from: { x: number; y: number }
  to: { x: number; y: number }
  isHighlighted?: boolean
  zoom: number
}) {
  const nodeWidth = 280
  const nodeHeight = 80
  
  const startX = from.x + nodeWidth / 2
  const startY = from.y + nodeHeight
  const endX = to.x + nodeWidth / 2
  const endY = to.y

  // Calculate control points for smooth curve
  const midY = (startY + endY) / 2
  const controlPoint1X = startX
  const controlPoint1Y = midY
  const controlPoint2X = endX
  const controlPoint2Y = midY

  const pathD = `M ${startX} ${startY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${endX} ${endY}`

  return (
    <g>
      <motion.path
        d={pathD}
        fill="none"
        stroke={isHighlighted ? '#FF6B00' : '#E2E8F0'}
        strokeWidth={(isHighlighted ? 3 : 2) / zoom}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="transition-all duration-300"
      />
      {/* Animated flow indicator */}
      {isHighlighted && (
        <motion.circle
          r={4 / zoom}
          fill="#FF6B00"
          initial={{ offsetDistance: '0%' }}
          animate={{ offsetDistance: '100%' }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          style={{ offsetPath: `path("${pathD}")` }}
        />
      )}
    </g>
  )
}

function WorkflowNodeCard({
  node,
  isSelected,
  onClick,
  onDragEnd,
  zoom,
}: {
  node: WorkflowNode
  isSelected: boolean
  onClick: () => void
  onDragEnd?: (id: string, position: { x: number; y: number }) => void
  zoom: number
}) {
  const config = nodeConfig[node.type]
  const Icon = config.icon

  return (
    <motion.div
      layoutId={node.id}
      drag
      dragMomentum={false}
      onDragEnd={(_, info) => {
        if (onDragEnd) {
          onDragEnd(node.id, {
            x: node.position.x + info.offset.x / zoom,
            y: node.position.y + info.offset.y / zoom,
          })
        }
      }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02, zIndex: 10 }}
      whileTap={{ scale: 0.98 }}
      style={{
        position: 'absolute',
        left: node.position.x,
        top: node.position.y,
        width: 280,
      }}
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded-xl border-2 bg-card p-4 shadow-md transition-all duration-200',
        config.borderColor,
        isSelected && 'ring-2 ring-primary ring-offset-2 shadow-accent'
      )}
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-3">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-lg shrink-0', config.bgColor)}>
          <Icon className={cn('h-5 w-5', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="truncate font-medium text-foreground">{node.title}</p>
          <p className="font-mono text-xs text-muted-foreground">{node.timestamp}</p>
        </div>
      </div>

      {/* Content Preview */}
      <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
        {node.content}
      </p>

      {/* Footer */}
      <div className="flex flex-wrap items-center gap-2">
        {node.droneId && (
          <Badge variant="outline" className="font-mono text-xs">
            {node.droneId}
          </Badge>
        )}
        {node.executionTime && (
          <Badge variant="secondary" className="gap-1 text-xs">
            <Clock className="h-3 w-3" />
            {node.executionTime}s
          </Badge>
        )}
        <Badge className={cn('text-xs capitalize', config.bgColor, config.color, 'border', config.borderColor)}>
          {node.type.replace('_', ' ')}
        </Badge>
      </div>
    </motion.div>
  )
}

function NodeDetailsSidebar({
  node,
  onClose,
}: {
  node: WorkflowNode
  onClose: () => void
}) {
  const config = nodeConfig[node.type]
  const Icon = config.icon
  const [copied, setCopied] = useState(false)

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(node, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="absolute right-0 top-0 h-full w-96 border-l border-border bg-card shadow-xl z-50"
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border p-4">
          <div className="flex items-center gap-3">
            <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', config.bgColor)}>
              <Icon className={cn('h-5 w-5', config.color)} />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">{node.title}</h3>
              <p className="font-mono text-xs text-muted-foreground">{node.timestamp}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-6">
            {/* Type Badge */}
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Type</p>
              <Badge className={cn('capitalize', config.bgColor, config.color, 'border', config.borderColor)}>
                {node.type.replace('_', ' ')}
              </Badge>
            </div>

            {/* Drone ID */}
            {node.droneId && (
              <div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Drone ID</p>
                <Badge variant="outline" className="font-mono">{node.droneId}</Badge>
              </div>
            )}

            {/* Content */}
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Reasoning / Content</p>
              <p className="rounded-lg bg-muted p-3 text-sm leading-relaxed text-foreground">
                {node.content}
              </p>
            </div>

            {/* Execution Time */}
            {node.executionTime && (
              <div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Execution Time</p>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className={cn(
                    'font-mono text-sm',
                    node.executionTime < 5 ? 'text-success' : 'text-warning'
                  )}>
                    {node.executionTime}s
                  </span>
                </div>
              </div>
            )}

            {/* Tool Args */}
            {node.toolArgs && Object.keys(node.toolArgs).length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Tool Arguments</p>
                <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs text-foreground">
                  {JSON.stringify(node.toolArgs, null, 2)}
                </pre>
              </div>
            )}

            {/* Result */}
            {node.result && Object.keys(node.result).length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Result</p>
                <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs text-foreground">
                  {JSON.stringify(node.result, null, 2)}
                </pre>
              </div>
            )}

            {/* Metadata */}
            {node.metadata && Object.keys(node.metadata).length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Metadata</p>
                <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs text-foreground">
                  {JSON.stringify(node.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="border-t border-border p-4">
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={handleCopyJson}
          >
            <Copy className="h-4 w-4" />
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </Button>
        </div>
      </div>
    </motion.div>
  )
}

export function WorkflowCanvas({ entries, onNodeSelect, selectedNodeId, zoom, onZoomChange }: WorkflowCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [nodes, setNodes] = useState<WorkflowNode[]>(() => generateNodePositions(entries))
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null)
  const [canvasSize, setCanvasSize] = useState({ width: 1600, height: 1200 })
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [startPan, setStartPan] = useState({ x: 0, y: 0 })

  // Update nodes when entries change
  useEffect(() => {
    setNodes(generateNodePositions(entries))
  }, [entries])

  // Update canvas size based on nodes
  useEffect(() => {
    if (nodes.length > 0) {
      const maxX = Math.max(...nodes.map(n => n.position.x)) + 400
      const maxY = Math.max(...nodes.map(n => n.position.y)) + 250
      setCanvasSize({
        width: Math.max(1600, maxX),
        height: Math.max(1200, maxY),
      })
    }
  }, [nodes])

  const handleNodeClick = useCallback((node: WorkflowNode) => {
    setSelectedNode(node)
    onNodeSelect?.(node)
  }, [onNodeSelect])

  const handleCloseDetails = useCallback(() => {
    setSelectedNode(null)
    onNodeSelect?.(null)
  }, [onNodeSelect])

  const handleDragEnd = useCallback((id: string, position: { x: number; y: number }) => {
    setNodes(prev => prev.map(node => 
      node.id === id ? { ...node, position } : node
    ))
  }, [])

  // Mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      const newZoom = Math.min(Math.max(zoom + delta, 0.5), 2.0)
      onZoomChange(newZoom)
    }
  }, [zoom, onZoomChange])

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only pan if clicking on canvas background, not on nodes
    if ((e.target as HTMLElement).closest('[data-node]')) return
    
    setIsPanning(true)
    setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }, [pan])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return
    setPan({
      x: e.clientX - startPan.x,
      y: e.clientY - startPan.y,
    })
  }, [isPanning, startPan])

  const handleMouseUp = useCallback(() => {
    setIsPanning(false)
  }, [])

  const resetView = useCallback(() => {
    onZoomChange(1)
    setPan({ x: 0, y: 0 })
  }, [onZoomChange])

  return (
    <div 
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-muted/20"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
    >
      {/* Canvas with transform */}
      <div
        ref={canvasRef}
        className="origin-top-left"
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          backgroundImage: `radial-gradient(circle, var(--border) 1px, transparent 1px)`,
          backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
          transition: isPanning ? 'none' : 'transform 0.1s ease-out',
        }}
      >
        {/* Connection Lines */}
        <svg
          className="pointer-events-none absolute inset-0"
          width={canvasSize.width}
          height={canvasSize.height}
        >
          {nodes.map((node, index) => {
            if (index === 0) return null
            const prevNode = nodes[index - 1]
            return (
              <ConnectionLine
                key={`connection-${prevNode.id}-${node.id}`}
                from={prevNode.position}
                to={node.position}
                isHighlighted={selectedNode?.id === node.id || selectedNode?.id === prevNode.id}
                zoom={zoom}
              />
            )
          })}
        </svg>

        {/* Nodes */}
        {nodes.map((node) => (
          <WorkflowNodeCard
            key={node.id}
            node={node}
            isSelected={selectedNode?.id === node.id}
            onClick={() => handleNodeClick(node)}
            onDragEnd={handleDragEnd}
            zoom={zoom}
          />
        ))}
      </div>

      {/* Zoom Controls - Fixed position */}
      <div className="absolute bottom-4 right-4 z-40 flex flex-col gap-2">
        <Button 
          variant="secondary" 
          size="icon" 
          className="h-10 w-10 rounded-full shadow-lg"
          onClick={() => onZoomChange(Math.min(zoom + 0.1, 2.0))}
        >
          <ZoomIn className="h-5 w-5" />
        </Button>
        <Button 
          variant="secondary" 
          size="icon" 
          className="h-10 w-10 rounded-full shadow-lg"
          onClick={() => onZoomChange(Math.max(zoom - 0.1, 0.5))}
        >
          <ZoomOut className="h-5 w-5" />
        </Button>
        <Button 
          variant="secondary" 
          size="icon" 
          className="h-10 w-10 rounded-full shadow-lg"
          onClick={resetView}
        >
          <Maximize2 className="h-5 w-5" />
        </Button>
        <div className="bg-background/90 backdrop-blur rounded-full px-3 py-1 text-xs font-mono text-center shadow-lg">
          {Math.round(zoom * 100)}%
        </div>
      </div>

      {/* Pan indicator */}
      {isPanning && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 rounded-full bg-background/90 px-4 py-2 shadow-lg backdrop-blur">
          <Move className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Panning</span>
        </div>
      )}

      {/* Details Sidebar */}
      <AnimatePresence>
        {selectedNode && (
          <NodeDetailsSidebar
            node={selectedNode}
            onClose={handleCloseDetails}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
