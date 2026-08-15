import React, { useState, useContext, useRef } from "react";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";

export const ModelUpload = ({ navigate, onCancel }) => {
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployError, setDeployError] = useState("");

  const { theme } = useContext(ThemeContext);

  const [validFiles, setValidFiles] = useState([]);
  const [invalidFiles, setInvalidFiles] = useState([]);

  const folderInputRef = useRef(null);
  const fileInputRef = useRef(null);

  const [modelName, setModelName] = useState("");
  const [description, setDescription] = useState("");
  const [modelType, setModelType] = useState("NLP");
  const [framework, setFramework] = useState("PyTorch");
  const [visibility, setVisibility] = useState("Private");
  const [runtime, setRuntime] = useState("CPU");
  const [entryFile, setEntryFile] = useState("main.py");
  const [version, setVersion] = useState("1.0.0");

  const allowedExtensions = [
    ".py",
    ".onnx",
    ".pkl",
    ".pickle",
    ".pt",
    ".pth",
    ".h5",
    ".joblib",
    ".ckpt",
    ".pb",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".md",
    ".log",
    ".env",
    ".gitignore",
    "dockerfile",
    "license",
    "readme",
  ];

  const isValidFile = (file) => {
    const name = file.name.toLowerCase();
    return allowedExtensions.some((ext) =>
      ext.startsWith(".") ? name.endsWith(ext) : name === ext,
    );
  };

  const parseModigFile = async (files) => {
    const modig = Array.from(files).find(
      (f) => f.name.toLowerCase() === ".modig",
    );
    if (!modig) return [];

    const content = await modig.text();
    return content
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));
  };

  const shouldIgnore = (filePath, ignorePatterns) => {
    return ignorePatterns.some((pattern) => {
      if (pattern.endsWith("/")) return filePath.includes(pattern);
      if (pattern.startsWith("*.")) return filePath.endsWith(pattern.slice(1));
      return filePath.includes(pattern);
    });
  };

  const processFiles = async (files) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    const ignorePatterns = await parseModigFile(fileArray);

    const newValid = [];
    const newInvalid = [];

    for (const file of fileArray) {
      const relativePath =
        file.webkitRelativePath && file.webkitRelativePath !== ""
          ? file.webkitRelativePath
          : file.name;

      if (file.name.toLowerCase() === ".modig") continue;
      if (shouldIgnore(relativePath, ignorePatterns)) continue;

      const wrappedFile = { file, relativePath };

      if (isValidFile(file)) {
        newValid.push(wrappedFile);
      } else {
        newInvalid.push(wrappedFile);
      }
    }

    const mergeUnique = (prev, next) => {
      const map = new Map();
      prev.forEach((f) => map.set(f.relativePath, f));
      next.forEach((f) => map.set(f.relativePath, f));
      return Array.from(map.values());
    };

    setValidFiles((prev) => mergeUnique(prev, newValid));
    setInvalidFiles((prev) => mergeUnique(prev, newInvalid));

    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  };

  const removeValidFile = (index) => {
    setValidFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const canDeploy = modelName.trim() !== "" && validFiles.length > 0;

  const handleDeploy = async () => {
    if (!canDeploy || isDeploying) return;

    setIsDeploying(true);
    setDeployError("");

    try {
      const formData = new FormData();

      // Metadata
      formData.append("model_name", modelName);
      formData.append("description", description);
      formData.append("model_type", modelType);
      formData.append("framework", framework);
      formData.append("visibility", visibility);
      formData.append("runtime", runtime);
      formData.append("entry_file", entryFile);
      formData.append("version", version);

      // Files
      validFiles.forEach(({ file, relativePath }) => {
        formData.append("files", file, relativePath);
      });

      const response = await fetch("http://localhost:8000/api/validate-model", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Server response not OK");
      }

      const data = await response.json();

      if (data.is_valid) {
        // ✅ SUCCESS → Navigate exactly like before
        navigate("registry");
        return;
      }

      // ❌ Backend says invalid
      setDeployError(data.error_message || "Model validation failed.");
    } catch (error) {
      setDeployError("Server error. Please try again.");
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div>
        <h1
          className={`text-3xl font-bold ${
            theme === "dark" ? "text-white" : "text-gray-900"
          }`}
        >
          Deploy New Model
        </h1>
        <p
          className={`mt-1 ${
            theme === "dark" ? "text-gray-400" : "text-gray-600"
          }`}
        >
          Upload and configure your AI model
        </p>
      </div>

      <div
        className={`p-6 rounded-xl border ${
          theme === "dark"
            ? "bg-gray-900/50 border-gray-800"
            : "bg-white border-gray-200"
        }`}
      >
        {/* Upload Section */}
        <div
          className={`border rounded-xl p-10 text-center ${
            theme === "dark"
              ? "border-gray-700 bg-gray-800/50"
              : "border-gray-300 bg-gray-50"
          }`}
        >
          <Upload
            className={`w-12 h-12 mx-auto mb-4 ${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            }`}
          />

          <h3
            className={`text-lg font-semibold mb-2 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Upload Model Files
          </h3>

          <p
            className={`mb-6 ${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            }`}
          >
            Select a full project folder or individual files
          </p>

          <div className="flex justify-center gap-4">
            <button
              type="button"
              onClick={() => folderInputRef.current?.click()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Browse Folder
            </button>

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Add Files
            </button>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            hidden
            multiple
            onChange={(e) => processFiles(e.target.files)}
          />

          <input
            type="file"
            ref={folderInputRef}
            hidden
            multiple
            webkitdirectory="true"
            directory=""
            onChange={(e) => processFiles(e.target.files)}
          />
        </div>

        {/* File Feedback */}
        {(validFiles.length > 0 || invalidFiles.length > 0) && (
          <div className="mt-6 space-y-6">
            {validFiles.length > 0 && (
              <div
                className={`rounded-lg p-4 border ${
                  theme === "dark"
                    ? "bg-green-900/20 border-green-700"
                    : "bg-green-50 border-green-200"
                }`}
              >
                <p className="font-semibold text-green-500 mb-3">
                  Accepted Files ({validFiles.length})
                </p>
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {validFiles.map((file, i) => (
                    <div
                      key={file.relativePath}
                      className={`flex justify-between items-center px-3 py-2 rounded-md text-sm ${
                        theme === "dark"
                          ? "bg-gray-800 text-gray-200"
                          : "bg-white text-gray-700"
                      }`}
                    >
                      <span className="truncate mr-4">{file.relativePath}</span>
                      <button
                        onClick={() => removeValidFile(i)}
                        className="text-red-500 hover:text-red-600 text-xs font-medium"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {invalidFiles.length > 0 && (
              <div
                className={`rounded-lg p-4 border ${
                  theme === "dark"
                    ? "bg-red-900/20 border-red-700"
                    : "bg-red-50 border-red-200"
                }`}
              >
                <p className="font-semibold text-red-500 mb-3">
                  Rejected Files ({invalidFiles.length})
                </p>
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {invalidFiles.map((file) => (
                    <div
                      key={file.relativePath}
                      className={`px-3 py-2 rounded-md text-sm ${
                        theme === "dark"
                          ? "bg-gray-800 text-gray-400"
                          : "bg-white text-gray-600"
                      }`}
                    >
                      {file.relativePath}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Metadata Form */}
        <div className="mt-6 space-y-6">
          <div>
            <label
              className={`block text-sm font-medium mb-2 ${
                theme === "dark" ? "text-gray-300" : "text-gray-700"
              }`}
            >
              Model Name *
            </label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className={`w-full p-3 rounded-lg border ${
                theme === "dark"
                  ? "bg-gray-800 border-gray-700 text-white"
                  : "bg-white border-gray-300 text-gray-900"
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            />
          </div>

          <div>
            <label
              className={`block text-sm font-medium mb-2 ${
                theme === "dark" ? "text-gray-300" : "text-gray-700"
              }`}
            >
              Description
            </label>
            <textarea
              rows="3"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={`w-full p-3 rounded-lg border ${
                theme === "dark"
                  ? "bg-gray-800 border-gray-700 text-white"
                  : "bg-white border-gray-300 text-gray-900"
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              {
                label: "Model Type",
                value: modelType,
                set: setModelType,
                options: [
                  "NLP",
                  "Computer Vision",
                  "Audio",
                  "Time Series",
                  "Reinforcement Learning",
                  "Multimodal",
                ],
              },
              {
                label: "Framework",
                value: framework,
                set: setFramework,
                options: [
                  "PyTorch",
                  "TensorFlow",
                  "ONNX",
                  "Scikit-Learn",
                  "Custom (Docker)",
                ],
              },
              {
                label: "Runtime",
                value: runtime,
                set: setRuntime,
                options: ["CPU", "GPU", "Auto-detect"],
              },
              {
                label: "Visibility",
                value: visibility,
                set: setVisibility,
                options: ["Private", "Organization", "Public"],
              },
            ].map((field) => (
              <div key={field.label}>
                <label
                  className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-gray-300" : "text-gray-700"
                  }`}
                >
                  {field.label}
                </label>
                <select
                  value={field.value}
                  onChange={(e) => field.set(e.target.value)}
                  className={`w-full p-3 rounded-lg border ${
                    theme === "dark"
                      ? "bg-gray-800 border-gray-700 text-white"
                      : "bg-white border-gray-300 text-gray-900"
                  } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                >
                  {field.options.map((opt) => (
                    <option key={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            ))}

            <div>
              <label
                className={`block text-sm font-medium mb-2 ${
                  theme === "dark" ? "text-gray-300" : "text-gray-700"
                }`}
              >
                Version
              </label>
              <input
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                className={`w-full p-3 rounded-lg border ${
                  theme === "dark"
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              />
            </div>

            <div>
              <label
                className={`block text-sm font-medium mb-2 ${
                  theme === "dark" ? "text-gray-300" : "text-gray-700"
                }`}
              >
                Entry File
              </label>
              <input
                type="text"
                value={entryFile}
                onChange={(e) => setEntryFile(e.target.value)}
                className={`w-full p-3 rounded-lg border ${
                  theme === "dark"
                    ? "bg-gray-800 border-gray-700 text-white"
                    : "bg-white border-gray-300 text-gray-900"
                } focus:outline-none focus:ring-2 focus:ring-blue-500`}
              />
            </div>
          </div>
        </div>

        {deployError && (
          <div
            className={`mt-6 rounded-lg p-4 border ${
              theme === "dark"
                ? "bg-red-900/20 border-red-700"
                : "bg-red-50 border-red-200"
            }`}
          >
            <p className="text-red-500 font-medium">{deployError}</p>
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3 pt-6">
          <button
            disabled={!canDeploy || isDeploying}
            className={`flex-1 px-6 py-3 rounded-lg transition-opacity ${
              canDeploy && !isDeploying
                ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:opacity-90"
                : "bg-gray-500 text-white cursor-not-allowed"
            }`}
            onClick={handleDeploy}
          >
            {isDeploying ? "Validating Model..." : "Deploy Model"}
          </button>

          <button
            onClick={onCancel}
            className={`px-6 py-3 rounded-lg border ${
              theme === "dark"
                ? "border-gray-700 hover:bg-gray-800 text-white"
                : "border-gray-300 hover:bg-gray-100 text-gray-900"
            }`}
          >
            Cancel
          </button>
        </div>
      </div>
    </motion.div>
  );
};