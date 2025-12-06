import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import GPUs from './pages/GPUs'
import GPUDetail from './pages/GPUDetail'
import Models from './pages/Models'
import Queue from './pages/Queue'
import Alarms from './pages/Alarms'
import { MegazordProvider } from './hooks/useMegazord'

function App() {
  return (
    <MegazordProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="gpus" element={<GPUs />} />
          <Route path="gpus/:hash" element={<GPUDetail />} />
          <Route path="models" element={<Models />} />
          <Route path="queue" element={<Queue />} />
          <Route path="alarms" element={<Alarms />} />
        </Route>
      </Routes>
    </MegazordProvider>
  )
}

export default App
