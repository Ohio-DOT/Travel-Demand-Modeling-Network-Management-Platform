import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import MainPage from './pages/MainPage';
import { MapProvider } from "./contexts/MapContext";

function App() {
    return (
    <>
        <MapProvider>
            <Router>
                {/* <NavBar /> */}
                <Routes>
                    <Route path="/" element={
                        <ProtectedRoute>
                            <MainPage />
                        </ProtectedRoute>
                    }/>
                    <Route path="/signup" element={<SignupPage />} />
                    <Route path="/login" element={<LoginPage />} />
                </Routes>
            </Router>
        </MapProvider>
    </>
    );
}

export default App;
