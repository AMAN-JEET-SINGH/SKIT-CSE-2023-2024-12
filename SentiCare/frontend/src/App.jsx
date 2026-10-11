import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import RiveHero from "./components/RiveHero";
import Home from "./pages/Home";
import DashboardLayout from "./components/DashboardLayout";
import DashboardHome from "./pages/DashboardHome";
import Sessions from "./pages/Sessions";
import Progress from "./pages/Progress";
import Resources from "./pages/Resources";
import Profile from "./pages/Profile";
import Calming from "./pages/Calming";
import { AuthProvider } from "./contexts/AuthContext";
import ThemeProvider from "./contexts/ThemeContext";
import useTheme from "./contexts/useTheme";
import ProtectedRoute from "./components/ProtectedRoute";

function AppContent() {
  const { theme } = useTheme();

  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<RiveHero />} />
          <Route path="/home" element={<Home />} />
          <Route path="/calming" element={<Calming />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardHome />} />
            <Route path="sessions" element={<Sessions />} />
            <Route path="progress" element={<Progress />} />
            <Route path="resources" element={<Resources />} />
            <Route path="profile" element={<Profile />} />
          </Route>
        </Routes>
        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme={theme}
        />
      </Router>
    </AuthProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
