import React, { useContext } from "react";
import { motion } from "framer-motion";
import { Plus, Box, ChevronRight } from "lucide-react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { ThemeContext } from "../context/ThemeContext";
import { dashboardStats, chartData, modelData } from "../data/mockData";

export const Dashboard = ({ navigate }) => {
  const { theme } = useContext(ThemeContext);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1
            className={`text-3xl font-bold ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Dashboard
          </h1>
          <p
            className={`${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            } mt-1`}
          >
            Overview of your AI model platform
          </p>
        </div>
        <button
          onClick={() => navigate("upload")}
          className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Deploy Model
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {dashboardStats.map((stat, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`p-6 rounded-xl border ${
              theme === "dark"
                ? "bg-gray-900/50 border-gray-800"
                : "bg-white border-gray-200"
            } backdrop-blur-sm`}
          >
            <div className="flex items-center justify-between mb-4">
              <stat.icon
                className={`w-8 h-8 ${
                  theme === "dark" ? "text-blue-400" : "text-blue-600"
                }`}
              />
              <span
                className={`text-sm font-medium ${
                  stat.trend === "up" ? "text-green-500" : "text-red-500"
                }`}
              >
                {stat.change}
              </span>
            </div>
            <h3
              className={`text-2xl font-bold ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}
            >
              {stat.value}
            </h3>
            <p
              className={`text-sm ${
                theme === "dark" ? "text-gray-400" : "text-gray-600"
              } mt-1`}
            >
              {stat.label}
            </p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div
          className={`p-6 rounded-xl border ${
            theme === "dark"
              ? "bg-gray-900/50 border-gray-800"
              : "bg-white border-gray-200"
          } backdrop-blur-sm`}
        >
          <h3
            className={`text-lg font-semibold mb-4 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            API Calls Overview
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={theme === "dark" ? "#374151" : "#e5e7eb"}
                vertical={false}
              />
              <XAxis
                dataKey="name"
                stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: theme === "dark" ? "#1f2937" : "#ffffff",
                  border: `1px solid ${
                    theme === "dark" ? "#374151" : "#e5e7eb"
                  }`,
                  borderRadius: "8px",
                }}
              />
              <Area
                type="monotone"
                dataKey="calls"
                stroke="#3b82f6"
                fillOpacity={1}
                fill="url(#colorCalls)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div
          className={`p-6 rounded-xl border ${
            theme === "dark"
              ? "bg-gray-900/50 border-gray-800"
              : "bg-white border-gray-200"
          } backdrop-blur-sm`}
        >
          <h3
            className={`text-lg font-semibold mb-4 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Average Latency (ms)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={theme === "dark" ? "#374151" : "#e5e7eb"}
                vertical={false}
              />
              <XAxis
                dataKey="name"
                stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: theme === "dark" ? "#1f2937" : "#ffffff",
                  border: `1px solid ${
                    theme === "dark" ? "#374151" : "#e5e7eb"
                  }`,
                  borderRadius: "8px",
                }}
              />
              <Line
                type="monotone"
                dataKey="latency"
                stroke="#8b5cf6"
                strokeWidth={3}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div
        className={`p-6 rounded-xl border ${
          theme === "dark"
            ? "bg-gray-900/50 border-gray-800"
            : "bg-white border-gray-200"
        } backdrop-blur-sm`}
      >
        <div className="flex items-center justify-between mb-4">
          <h3
            className={`text-lg font-semibold ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Recent Models
          </h3>
          <button
            className={`text-sm ${
              theme === "dark" ? "text-blue-400" : "text-blue-600"
            } hover:underline`}
            onClick={() => navigate("registry")}
          >
            View all
          </button>
        </div>
        <div className="space-y-3">
          {modelData.map((model) => (
            <div
              key={model.id}
              onClick={() => navigate("detail")}
              className={`p-4 rounded-lg border ${
                theme === "dark"
                  ? "bg-gray-800/50 border-gray-700 hover:bg-gray-800"
                  : "bg-gray-50 border-gray-200 hover:bg-gray-100"
              } flex items-center justify-between cursor-pointer transition-colors`}
            >
              <div className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-lg ${
                    theme === "dark" ? "bg-gray-700" : "bg-gray-200"
                  } flex items-center justify-center`}
                >
                  <Box className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4
                      className={`font-medium ${
                        theme === "dark" ? "text-white" : "text-gray-900"
                      }`}
                    >
                      {model.name}
                    </h4>
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        model.visibility === "public"
                          ? "bg-green-500/20 text-green-500"
                          : model.visibility === "private"
                          ? "bg-red-500/20 text-red-500"
                          : "bg-blue-500/20 text-blue-500"
                      }`}
                    >
                      {model.visibility}
                    </span>
                  </div>
                  <p
                    className={`text-sm ${
                      theme === "dark" ? "text-gray-400" : "text-gray-600"
                    }`}
                  >
                    {model.type} • {model.calls} calls • {model.latency} avg
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    model.status === "active"
                      ? "bg-green-500/20 text-green-500"
                      : model.status === "deploying"
                      ? "bg-yellow-500/20 text-yellow-500"
                      : "bg-gray-500/20 text-gray-500"
                  }`}
                >
                  {model.status}
                </span>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};
