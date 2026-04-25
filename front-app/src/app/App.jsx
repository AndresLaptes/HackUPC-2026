import { useState } from 'react'
import Providers from './providers'
import CaseView from './CaseView'
import CasePicker from '../presentation/ui/CasePicker'
import TabBar from '../presentation/ui/TabBar'

export default function App() {
  return (
    <Providers>
      <MultiViewApp />
    </Providers>
  )
}

function MultiViewApp() {
  const [openCases, setOpenCases] = useState([])   // [{id, caseName}]
  const [activeId, setActiveId]   = useState(null)
  const [showPicker, setShowPicker] = useState(true)
  const [solveRequest, setSolveRequest] = useState({ token: 0, caseId: null })
  const [solvingCaseId, setSolvingCaseId] = useState(null)

  function openCase(caseName) {
    const existing = openCases.find((c) => c.caseName === caseName)
    if (existing) {
      setActiveId(existing.id)
      setShowPicker(false)
      return
    }
    const id = crypto.randomUUID()
    setOpenCases((prev) => [...prev, { id, caseName }])
    setActiveId(id)
    setShowPicker(false)
  }

  function closeCase(id) {
    const remaining = openCases.filter((c) => c.id !== id)
    setOpenCases(remaining)
    if (activeId === id) {
      const last = remaining[remaining.length - 1]
      setActiveId(last?.id ?? null)
      if (!remaining.length) setShowPicker(true)
    }
  }

  const activeCase = openCases.find((c) => c.id === activeId)

  function runActiveCaseAlgorithm() {
    if (!activeCase || solvingCaseId) return
    setSolvingCaseId(activeCase.id)
    setSolveRequest((prev) => ({ token: prev.token + 1, caseId: activeCase.id }))
  }

  function handleSolveDone(caseId) {
    if (solvingCaseId === caseId) {
      setSolvingCaseId(null)
    }
  }

  return (
    <div style={styles.root}>
      {openCases.length > 0 && (
        <TabBar
          cases={openCases}
          activeId={activeId}
          onSwitch={setActiveId}
          onClose={closeCase}
          onAdd={() => setShowPicker(true)}
          onRunAlgorithm={runActiveCaseAlgorithm}
          canRunAlgorithm={Boolean(activeCase)}
          solving={Boolean(solvingCaseId)}
        />
      )}

      <div style={styles.body}>
        {showPicker ? (
          <CasePicker
            onSelect={openCase}
            canClose={openCases.length > 0}
            onClose={() => setShowPicker(false)}
          />
        ) : activeCase ? (
          <CaseView
            key={activeCase.id}
            caseId={activeCase.id}
            caseName={activeCase.caseName}
            solveToken={solveRequest.token}
            solveForCaseId={solveRequest.caseId}
            onSolveDone={handleSolveDone}
          />
        ) : null}
      </div>
    </div>
  )
}

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    width: '100vw',
    height: '100dvh',
    overflow: 'hidden',
    background: '#060c10',
  },
  body: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
  },
}
