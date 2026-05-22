import { CognitiveProgressCard } from './components/CognitiveProgressCard'
import { FeatureStatusBar } from './components/FeatureStatusBar'
import { HardeningShieldCard } from './components/HardeningShieldCard'
import { LiveConsole } from './components/LiveConsole'
import { MasterHeader } from './components/MasterHeader'
import { TokenCounterCard } from './components/TokenCounterCard'
import { usePlumberPolling } from './hooks/usePlumberPolling'

export default function App() {
  const {
    state,
    logs,
    config,
    connectionStatus,
    lastUpdatedAt,
    frozen,
    engineBusy,
    startEngine,
    stopEngine,
    saveConfig,
  } = usePlumberPolling()

  return (
    <div className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 lg:grid-cols-2">
        <MasterHeader
          state={state}
          connectionStatus={connectionStatus}
          lastUpdatedAt={lastUpdatedAt}
          config={config}
          frozen={frozen}
          engineBusy={engineBusy}
          onStartEngine={startEngine}
          onStopEngine={stopEngine}
          onSaveConfig={saveConfig}
        />

        <FeatureStatusBar
          daemonStatus={state?.status}
          config={config}
          frozen={frozen}
        />

        <div className="lg:col-span-2">
          <CognitiveProgressCard state={state} />
        </div>

        <TokenCounterCard
          promptTokens={state?.session_prompt_tokens ?? 0}
          completionTokens={state?.session_completion_tokens ?? 0}
        />

        <HardeningShieldCard config={config} />

        <LiveConsole logs={logs} />
      </div>
    </div>
  )
}
