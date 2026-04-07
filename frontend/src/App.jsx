import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Layout from './components/layout/Layout';
import CustomCursor from './components/ui/CustomCursor';
import Landing from './pages/Landing';
import About from './pages/About';
import Dashboard from './pages/Dashboard';
import StartBatch from './pages/Dashboard/StartBatch';
import DailyCheckin from './pages/Dashboard/DailyCheckin';
import BatchHistory from './pages/Dashboard/BatchHistory';
import Report from './pages/Report';
import Settings from './pages/Settings';

function App() {
  const location = useLocation();

  return (
    <>
      <CustomCursor />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Landing />} />
            <Route path="about" element={<About />} />
            <Route path="report" element={<Report />} />
            <Route path="settings" element={<Settings />} />
            
            <Route path="dashboard" element={<Dashboard />}>
              {/* Dashboard Layout handles its own nested routes if necessary, 
                  but we'll flatten them here and use the sidebar inside those components or layout */}
              <Route path="new" element={<StartBatch />} />
              <Route path="checkin" element={<DailyCheckin />} />
              <Route path="history" element={<BatchHistory />} />
            </Route>
          </Route>
        </Routes>
      </AnimatePresence>
    </>
  );
}

export default App;
