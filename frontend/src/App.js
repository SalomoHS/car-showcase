import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import CarShowcase from "./components/CarShowcase";
import LandingPage from "./components/LandingPage";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/showcase" element={<CarShowcase />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;