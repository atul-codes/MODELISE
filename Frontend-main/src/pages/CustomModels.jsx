import React, { useContext, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plug, Plus, Trash2, Power, Loader2 } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";
import { api } from "../lib/api";

const cardClass = (theme) =>
  `p-6 rounded-xl border ${
    theme === "dark" ? "bg-gray-900/50 border-gray-800" : "bg-white border-gray-200"
  } backdrop-blur-sm`;

const inputClass = (theme) =>
  `w-full p-2.5 rounded-lg border text-sm ${
    theme === "dark" ? "bg-gray-900 border-gray-700 text-white" : "bg-white border-gray-300 text-gray-900"
  } focus:outline-none focus:ring-2 focus:ring-blue-500`;

export const CustomModels = ({ token }) => {
  const { theme } = useContext(ThemeContext);
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: "",
    base_url: "",
    request_style: "openai_chat",
    auth_header_name: "",
    auth_header_value: "",
  });

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setEndpoints(await api.listCustomModels(token));
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

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { ...form };
      if (!payload.auth_header_name) delete payload.auth_header_name;
      if (!payload.auth_header_value) delete payload.auth_header_value;
      await api.createCustomModel(token, payload);
      setForm({ name: "", base_url: "", request_style: "openai_chat", auth_header_name: "", auth_header_value: "" });
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id, enabled) => {
    await api.toggleCustomModel(token, id, !enabled);
    load();
  };

  const handleDelete = async (id) => {
    await api.deleteCustomModel(token, id);
    load();
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>Custom Models</h1>
          <p className={`${theme === "dark" ? "text-gray-400" : "text-gray-600"} mt-1`}>
            Connect a self-hosted model you already have running. Every prompt sent to it is chained through
            Layer 1 and Layer 2 first, automatically.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Connect Model
        </button>
      </div>

      {error && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {showForm && (
        <motion.form
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          onSubmit={handleCreate}
          className={cardClass(theme) + " space-y-4"}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="My local Ollama" className={inputClass(theme)} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Endpoint URL</label>
              <input required value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                placeholder="http://localhost:11434/v1/chat/completions" className={inputClass(theme)} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Request style</label>
              <select value={form.request_style} onChange={(e) => setForm({ ...form, request_style: e.target.value })}
                className={inputClass(theme)}>
                <option value="openai_chat">OpenAI-style chat (Ollama, vLLM, LM Studio)</option>
                <option value="raw_text">Raw text ({"{ prompt: ... }"} in, plain text out)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Auth header name (optional)</label>
              <input value={form.auth_header_name} onChange={(e) => setForm({ ...form, auth_header_name: e.target.value })}
                placeholder="Authorization" className={inputClass(theme)} />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-medium text-gray-500 mb-1 block">Auth header value (optional, encrypted at rest)</label>
              <input type="password" value={form.auth_header_value} onChange={(e) => setForm({ ...form, auth_header_value: e.target.value })}
                placeholder="Bearer sk-..." className={inputClass(theme)} />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2">
              {saving && <Loader2 className="w-4 h-4 animate-spin" />} Save Endpoint
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className={`px-4 py-2 rounded-lg border ${theme === "dark" ? "border-gray-700 text-gray-300" : "border-gray-300 text-gray-700"}`}>
              Cancel
            </button>
          </div>
        </motion.form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : endpoints.length === 0 ? (
          <p className="text-gray-500">No custom models connected yet.</p>
        ) : (
          endpoints.map((ep) => (
            <div key={ep.id} className={cardClass(theme)}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                    <Plug className="w-5 h-5 text-blue-500" />
                  </div>
                  <div>
                    <h3 className={`font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>{ep.name}</h3>
                    <p className="text-xs text-gray-500 break-all">{ep.base_url}</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${ep.enabled ? "bg-green-500/20 text-green-500" : "bg-gray-500/20 text-gray-500"}`}>
                  {ep.enabled ? "ENABLED" : "DISABLED"}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-4 text-xs text-gray-500">
                <span>{ep.request_style}</span>
                {ep.has_auth && <span>auth configured</span>}
              </div>
              <div className="flex gap-2 mt-4">
                <button onClick={() => handleToggle(ep.id, ep.enabled)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium border ${theme === "dark" ? "border-gray-700 hover:bg-gray-800 text-gray-300" : "border-gray-300 hover:bg-gray-100 text-gray-700"}`}>
                  <Power className="w-3 h-3" /> {ep.enabled ? "Disable" : "Enable"}
                </button>
                <button onClick={() => handleDelete(ep.id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium border border-red-500/20 text-red-400 hover:bg-red-500/10">
                  <Trash2 className="w-3 h-3" /> Remove
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
};
