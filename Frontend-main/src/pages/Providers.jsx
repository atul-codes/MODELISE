import React, { useContext, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Power, Plus, X, Loader2, Layers } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";
import { api } from "../lib/api";

const cardClass = (theme) =>
  `p-5 rounded-xl border ${
    theme === "dark" ? "bg-gray-900/50 border-gray-800" : "bg-white border-gray-200"
  } backdrop-blur-sm`;

const KNOWN_PIPELINES = ["custom_model_default", "commercial_ai_default"];

const STAGE_COLORS = {
  layer1: "bg-orange-500/10 text-orange-500",
  layer2: "bg-blue-500/10 text-blue-500",
  geo: "bg-purple-500/10 text-purple-500",
};

export const Providers = ({ token }) => {
  const { theme } = useContext(ThemeContext);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newPipelineInput, setNewPipelineInput] = useState({});

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setProviders(await api.listProviders(token));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleToggle = async (id, enabled) => {
    setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, enabled: !enabled } : p)));
    try {
      await api.toggleProvider(token, id, !enabled);
    } catch (err) {
      setError(err.message);
      load();
    }
  };

  const updateAttachments = async (id, pipelines) => {
    setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, attached_pipelines: pipelines } : p)));
    try {
      await api.setProviderAttachments(token, id, pipelines);
    } catch (err) {
      setError(err.message);
      load();
    }
  };

  const togglePipeline = (provider, pipeline) => {
    const has = provider.attached_pipelines.includes(pipeline);
    const next = has
      ? provider.attached_pipelines.filter((p) => p !== pipeline)
      : [...provider.attached_pipelines, pipeline];
    updateAttachments(provider.id, next);
  };

  const addCustomPipeline = (provider) => {
    const value = (newPipelineInput[provider.id] || "").trim();
    if (!value || provider.attached_pipelines.includes(value)) return;
    updateAttachments(provider.id, [...provider.attached_pipelines, value]);
    setNewPipelineInput((s) => ({ ...s, [provider.id]: "" }));
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className={`text-3xl font-bold flex items-center gap-2 ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
          <ShieldCheck className="w-7 h-7 text-blue-500" /> Plug-and-Play Providers
        </h1>
        <p className={`${theme === "dark" ? "text-gray-400" : "text-gray-600"} mt-1 max-w-3xl`}>
          Every inspection backend, Layer 1's heuristic screen, the image check, both Layer 2 engines, and every
          geo-compliance pack, is a row here. Toggle any of them on or off, and attach any of them to any pipeline.
          This is the whole mechanism: no code change, no redeploy, just checkboxes.
        </p>
      </div>

      {error && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="space-y-3">
          {providers.map((p) => (
            <div key={p.id} className={cardClass(theme)}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${STAGE_COLORS[p.stage] || "bg-gray-500/10 text-gray-500"}`}>
                    {p.stage}
                  </span>
                  <div>
                    <h3 className={`font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>{p.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                    <p className="text-[10px] text-gray-600 mt-1 font-mono">{p.kind}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleToggle(p.id, p.enabled)}
                  className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border ${
                    p.enabled
                      ? "border-green-500/30 bg-green-500/10 text-green-500"
                      : theme === "dark"
                      ? "border-gray-700 text-gray-400"
                      : "border-gray-300 text-gray-500"
                  }`}
                >
                  <Power className="w-3 h-3" /> {p.enabled ? "Enabled" : "Disabled"}
                </button>
              </div>

              <div className={`mt-4 pt-4 border-t ${theme === "dark" ? "border-gray-800" : "border-gray-100"}`}>
                <p className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" /> Attached pipelines
                </p>
                <div className="flex flex-wrap gap-2 items-center">
                  {KNOWN_PIPELINES.map((pipeline) => {
                    const active = p.attached_pipelines.includes(pipeline);
                    return (
                      <button
                        key={pipeline}
                        onClick={() => togglePipeline(p, pipeline)}
                        className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                          active
                            ? "bg-blue-500 border-blue-500 text-white"
                            : theme === "dark"
                            ? "border-gray-700 text-gray-400 hover:border-gray-600"
                            : "border-gray-300 text-gray-500 hover:border-gray-400"
                        }`}
                      >
                        {pipeline}
                      </button>
                    );
                  })}
                  {p.attached_pipelines
                    .filter((pl) => !KNOWN_PIPELINES.includes(pl))
                    .map((pl) => (
                      <span key={pl} className="px-2.5 py-1 rounded-full text-xs bg-blue-500 text-white flex items-center gap-1.5">
                        {pl}
                        <button onClick={() => togglePipeline(p, pl)}><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                  <div className="flex items-center gap-1">
                    <input
                      value={newPipelineInput[p.id] || ""}
                      onChange={(e) => setNewPipelineInput((s) => ({ ...s, [p.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCustomPipeline(p))}
                      placeholder="custom pipeline name..."
                      className={`px-2 py-1 rounded-full text-xs border w-36 ${theme === "dark" ? "bg-gray-900 border-gray-700 text-white" : "bg-white border-gray-300 text-gray-900"}`}
                    />
                    <button onClick={() => addCustomPipeline(p)} className="p-1 rounded-full border border-gray-700 text-gray-400 hover:text-white">
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};
