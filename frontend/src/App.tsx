import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Home from "./pages/Home/Home";
import Play from "./pages/Play/Play";
import Analysis from "./pages/Analysis/Analysis";
import Login from "./pages/Login/Login";
import ProtectedRoute from "./components/ProtectedRoute";

import Navbar from "./components/Navbar/Navbar";

function App() {
  return (
    <AuthProvider>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/play"
          element={
            <ProtectedRoute>
              <Play />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analysis"
          element={
            <ProtectedRoute>
              <Analysis />
            </ProtectedRoute>
          }
        />
        
      </Routes>
    </AuthProvider>
  );
}

export default App;