import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProject } from '@/hooks/useProject'
import { useWebSocket } from '@/hooks/useWebSocket'
import { StageNavigation } from '@/components/common/StageNavigation'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ResearchPanel } from '@/components/research/ResearchPanel'
import { TopicPanel } from '@/components/topics/TopicPanel'
import { ScriptPanel } from '@/components/script/ScriptPanel'
import { AudioPanel } from '@/components/audio/AudioPanel'
import { VisualPanel } from '@/components/visual/VisualPanel'
import { RenderPanel } from '@/components/render/RenderPanel'
import type { PipelineStage } from '@/types'

export function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { project, loading, error } = useProject(projectId)
  const { lastMessage } = useWebSocket(projectId)
  const [activeStage, setActiveStage] = useState<PipelineStage>('RESEARCH')

  if (loading) return <div className="p-6 text-gray-500">Loading project...</div>
  if (error || !project) return <div className="p-6 text-red-500">{error ?? 'Project not found'}</div>

  const panel = () => {
    switch (activeStage) {
      case 'RESEARCH': return <ResearchPanel projectId={project.id} lastMessage={lastMessage} />
      case 'TOPIC': return <TopicPanel projectId={project.id} lastMessage={lastMessage} />
      case 'SCRIPT': return <ScriptPanel projectId={project.id} />
      case 'AUDIO': return <AudioPanel projectId={project.id} lastMessage={lastMessage} onStageChange={setActiveStage} />
      case 'VISUAL': return <VisualPanel projectId={project.id} lastMessage={lastMessage} />
      case 'RENDER': return <RenderPanel projectId={project.id} lastMessage={lastMessage} />
    }
  }

  return (
    <div className="flex h-screen">
      <div className="border-r bg-gray-50 flex flex-col">
        <button onClick={() => navigate('/')} className="px-4 py-3 text-sm text-gray-500 hover:text-gray-700 text-left">
          ← Projects
        </button>
        <StageNavigation
          currentStage={project.current_stage}
          activeStage={activeStage}
          onStageSelect={setActiveStage}
        />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b px-6 py-3 flex items-center justify-between bg-white">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{project.title}</h1>
            {project.description && <p className="text-sm text-gray-500">{project.description}</p>}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">{project.current_stage}</span>
            <StatusBadge status={project.status} />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {panel()}
        </main>
      </div>
    </div>
  )
}
