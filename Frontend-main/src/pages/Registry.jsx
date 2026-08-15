import React, { useContext } from "react";
import { motion } from "framer-motion";
import { Box, ChevronRight } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";
import { ModelContext } from "../context/ModelContext";

export const Registry = ({ navigate }) => {
  const { theme } = useContext(ThemeContext);
  const { models } = useContext(ModelContext);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div>
        <h1
          className={`text-3xl font-bold ${
            theme === "dark" ? "text-white" : "text-gray-900"
          }`}
        >
          Model Registry
        </h1>
        <p
          className={`mt-1 ${
            theme === "dark" ? "text-gray-400" : "text-gray-600"
          }`}
        >
          All deployed models in your workspace
        </p>
      </div>

      <div
        className={`p-6 rounded-xl border ${
          theme === "dark"
            ? "bg-gray-900/50 border-gray-800"
            : "bg-white border-gray-200"
        } backdrop-blur-sm`}
      >
        {models.length === 0 ? (
          <div
            className={`text-center py-10 ${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            }`}
          >
            No models deployed yet.
          </div>
        ) : (
          <div className="space-y-3">
            {models.map((model) => (
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
                          theme === "dark"
                            ? "text-white"
                            : "text-gray-900"
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
                        theme === "dark"
                          ? "text-gray-400"
                          : "text-gray-600"
                      }`}
                    >
                      {model.type} • v{model.version} • {model.framework} • {model.runtime}
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
        )}
      </div>
    </motion.div>
  );
};