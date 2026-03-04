import type { PipelineStage } from '@/types'

const stages: { key: PipelineStage; label: string; icon: string }[] = [
  { key: 'RESEARCH', label: 'Research', icon: '🔍' },
  { key: 'TOPIC', label: 'Topics', icon: '💡' },
  { key: 'SCRIPT', label: 'Script', icon: '📝' },
  { key: 'AUDIO', label: 'Audio', icon: '🎙️' },
  { key: 'VISUAL', label: 'Visuals', icon: '🎬' },
  { key: 'RENDER', label: 'Render', icon: '🎞️' },
]

const stageOrder: PipelineStage[] = stages.map(s => s.key)

interface Props {
  currentStage: PipelineStage
  activeStage: PipelineStage
  onStageSelect: (stage: PipelineStage) => void
}

export function StageNavigation({ currentStage, activeStage, onStageSelect }: Props) {
  const currentIdx = stageOrder.indexOf(currentStage)

  return (
    <nav className="flex flex-col gap-1 w-48 p-3" role="navigation" aria-label="Pipeline stages">
      {stages.map((stage, idx) => {
        const isActive = stage.key === activeStage
        const isCompleted = idx < currentIdx
        return (
          <button
            key={stage.key}
            onClick={() => onStageSelect(stage.key)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors
              ${isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'}
              ${isCompleted ? 'opacity-100' : ''}`}
            aria-current={isActive ? 'step' : undefined}
          >
            <span className="text-base">{stage.icon}</span>
            <span>{stage.label}</span>
            {isCompleted && <span className="ml-auto text-green-500 text-xs">✓</span>}
          </button>
        )
      })}
    </nav>
  )
}
