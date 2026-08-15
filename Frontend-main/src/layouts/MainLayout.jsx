import React, { useContext } from "react";
import { ThemeContext } from "../context/ThemeContext";

import { AnimatePresence } from "framer-motion";
import { 
  LayoutDashboard, Box, Activity, CreditCard, Settings, 
  Sparkles, LogOut, Sun, Moon, Bell, HelpCircle, 
  ChevronDown, Book, Plug, MessageSquare, Globe, ShieldCheck
} from 'lucide-react';

export const MainLayout = ({
  children,
  currentView,
  setView,
  onLogout,
  user,
}) => {
  const { theme, toggleTheme } = useContext(ThemeContext);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "registry", label: "Registry", icon: Box },
    { id: "custom-models", label: "Custom Models", icon: Plug },
    { id: "commercial-chat", label: "Commercial AI Chat", icon: MessageSquare },
    { id: "geo-compliance", label: "Geo-Compliance", icon: Globe },
    { id: "providers", label: "Plug-and-Play", icon: ShieldCheck },
    { id: "activity", label: "Activity", icon: Activity },
    { id: "billing", label: "Billing", icon: CreditCard },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div
      className={`flex h-screen ${
        theme === "dark"
          ? "bg-gray-950 text-gray-100"
          : "bg-gray-50 text-gray-900"
      }`}
    >
      {/* Sidebar */}
      <aside
        className={`w-64 border-r ${
          theme === "dark"
            ? "border-gray-800 bg-gray-900"
            : "border-gray-200 bg-white"
        } hidden md:flex flex-col`}
      >
        <div className="p-6 flex items-center gap-2 border-b border-dashed border-gray-800/50">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">MODELISE</span>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentView === item.id
                  ? "bg-blue-500/10 text-blue-500"
                  : "text-gray-500 hover:bg-gray-800/50 hover:text-gray-300"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-800/50">
          <div
            className={`rounded-lg p-4 mb-4 ${
              theme === "dark" ? "bg-gray-800" : "bg-gray-100"
            }`}
          >
            <div className="flex justify-between text-xs mb-2">
              <span className="text-gray-500">Credits Used</span>
              <span className="font-semibold text-blue-500">
                {user.credits}%
              </span>
            </div>
            <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500"
                style={{ width: `${user.credits}%` }}
              ></div>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header
          className={`h-16 border-b flex items-center justify-between px-6 ${
            theme === "dark"
              ? "border-gray-800 bg-gray-950/50"
              : "border-gray-200 bg-white/50"
          } backdrop-blur-md sticky top-0 z-10`}
        >
          {/* Left: Context / Org Switcher */}
          <div className="flex items-center gap-4">
            <button
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
                theme === "dark"
                  ? "border-gray-800 hover:bg-gray-800 text-gray-300"
                  : "border-gray-200 hover:bg-gray-100 text-gray-700"
              }`}
            >
              <div className="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center text-[10px] text-white font-bold">
                A
              </div>
              <span className="text-sm font-medium">Acme Corp</span>
              <ChevronDown className="w-3 h-3 opacity-50" />
            </button>
            <span className="text-gray-600 font-light text-xl">/</span>
            <div className="flex items-center gap-2">
              <span
                className={`text-sm font-medium ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}
              >
                Production
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/20 text-green-500 border border-green-500/20">
                US-EAST
              </span>
            </div>
          </div>

          {/* Right: Global Actions */}
          <div className="flex items-center gap-3">
            <button
              className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                theme === "dark"
                  ? "text-gray-400 hover:text-white hover:bg-gray-800"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              <Book className="w-4 h-4" />
              <span>Docs</span>
            </button>

            <div
              className={`h-6 w-px ${
                theme === "dark" ? "bg-gray-800" : "bg-gray-300"
              } mx-1 hidden md:block`}
            ></div>

            <button
              className={`p-2 rounded-full transition-colors ${
                theme === "dark"
                  ? "text-gray-400 hover:bg-gray-800 hover:text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <HelpCircle className="w-5 h-5" />
            </button>

            <button
              className={`relative p-2 rounded-full transition-colors ${
                theme === "dark"
                  ? "text-gray-400 hover:bg-gray-800 hover:text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2.5 w-2 h-2 bg-red-500 rounded-full border-2 border-transparent"></span>
            </button>

            <button
              onClick={toggleTheme}
              className={`p-2 rounded-full transition-colors ${
                theme === "dark"
                  ? "text-gray-400 hover:bg-gray-800 hover:text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              {theme === "dark" ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>

            <div className="ml-2 w-8 h-8 rounded-full bg-gradient-to-r from-pink-500 to-orange-400 cursor-pointer hover:ring-2 hover:ring-offset-2 ring-blue-500 transition-all"></div>
          </div>
        </header>

        {/* Scrollable Page Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          <AnimatePresence mode="wait">{children}</AnimatePresence>
        </div>
      </main>
    </div>
  );
};
