import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { Dashboard } from './pages/Dashboard';
import { Production } from './pages/Production';
import { Consumption } from './pages/Consumption';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/production" element={<Production />} />
          <Route path="/consumption" element={<Consumption />} />
        </Routes>

        {/* Footer */}
        <footer className="footer">
          <p>Veri Kaynagi: EPIAS Seffaflik Platformu</p>
          <p>Model: Facebook Prophet | Otomatik Guncelleme: Her Gece 02:00</p>
          <p className="footer-note">GitHub Actions ile otomatik tahmin & karşılaştırma sistemi</p>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
