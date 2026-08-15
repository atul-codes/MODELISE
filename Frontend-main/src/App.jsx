import React, { useState } from "react";

import { ThemeContext } from "./context/ThemeContext";
import { ModelProvider } from "./context/ModelContext";
import { MainLayout as Layout } from "./layouts/MainLayout";

import { AuthPage } from "./pages/AuthPage";
import { Dashboard } from "./pages/Dashboard";
import { ModelUpload } from "./pages/ModelUpload";
import { ModelDetail } from "./pages/ModelDetail";
import { Registry } from "./pages/Registry";
import { CustomModels } from "./pages/CustomModels";
import { CommercialChat } from "./pages/CommercialChat";
import { GeoCompliance } from "./pages/GeoCompliance";
import { Providers } from "./pages/Providers";

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [token, setToken] = useState(null);
  const [currentView, setCurrentView] = useState("dashboard");

  const [user, setUser] = useState({
    name: "ansham",
    age: 12,
    credits: 89,
  });

  const toggleTheme = () =>
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));

  const handleLogin = (accessToken) => {
    setToken(accessToken);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setToken(null);
    setIsLoggedIn(false);
  };

  const renderView = () => {
    switch (currentView) {
      case "dashboard":
        return <Dashboard key="dash" navigate={setCurrentView} />;
      case "registry":
        return <Registry key="registry" navigate={setCurrentView} />;
      case "upload":
        return (
          <ModelUpload
            key="upload"
            navigate={setCurrentView}
            onCancel={() => setCurrentView("dashboard")}
          />
        );
      case "detail":
        return (
          <ModelDetail
            key="detail"
            onBack={() => setCurrentView("dashboard")}
          />
        );
      case "custom-models":
        return <CustomModels key="custom-models" token={token} />;
      case "commercial-chat":
        return <CommercialChat key="commercial-chat" token={token} />;
      case "geo-compliance":
        return <GeoCompliance key="geo-compliance" token={token} />;
      case "providers":
        return <Providers key="providers" token={token} />;
      default:
        return (
          <div className="text-center py-20 text-gray-500">
            Page under construction
          </div>
        );
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {isLoggedIn ? (
        <ModelProvider>
          <Layout
            currentView={currentView}
            setView={setCurrentView}
            onLogout={handleLogout}
            user={user}
          >
            {renderView()}
          </Layout>
        </ModelProvider>
      ) : (
        <AuthPage onLogin={handleLogin} />
      )}
    </ThemeContext.Provider>
  );
}
