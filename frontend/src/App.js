import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import CarShowcase from "./components/CarShowcase";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<CarShowcase />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;