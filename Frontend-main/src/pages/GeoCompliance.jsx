import React, { useContext, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Globe, UploadCloud, Power, Loader2, FileText, FileSpreadsheet } from "lucide-react";
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

export const GeoCompliance = ({ token }) => {
  const { theme } = useContext(ThemeContext);
  const [packs, setPacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const [form, setForm] = useState({ pack_id: "", display_name: "", country_code: "" });
  const [file, setFile] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setPacks(await api.listGeoPacks(token));
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

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const isCsv = file.name.toLowerCase().endsWith(".csv");
      const fn = isCsv ? api.uploadGeoPackCsv : api.uploadGeoPackPdf;
      await fn(token, form.pack_id, form.display_name, form.country_code || null, file);
      setForm({ pack_id: "", display_name: "", country_code: "" });
      setFile(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleToggle = async (packId, enabled) => {
    await api.toggleGeoPack(token, packId, !enabled);
    load();
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className={`text-3xl font-bold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>Geo-Compliance</h1>
        <p className={`${theme === "dark" ? "text-gray-400" : "text-gray-600"} mt-1`}>
          Each country/regime gets its own pack with embeddings built once at upload - uploading a new pack never
          touches or re-embeds any other pack. Toggle a pack on to enforce it; it can be attached to any pipeline,
          including Layer 1's, from the Plug-and-Play page.
        </p>
      </div>

      {error && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      <form onSubmit={handleUpload} className={cardClass(theme) + " space-y-4"}>
        <h3 className={`font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>Upload a new pack</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">Pack ID (slug)</label>
            <input required value={form.pack_id} onChange={(e) => setForm({ ...form, pack_id: e.target.value })}
              placeholder="in_dpdp" className={inputClass(theme)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">Display name</label>
            <input required value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              placeholder="India - DPDP Act" className={inputClass(theme)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500 mb-1 block">Country code (optional)</label>
            <input value={form.country_code} onChange={(e) => setForm({ ...form, country_code: e.target.value })}
              placeholder="IN" className={inputClass(theme)} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className={`flex-1 flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer text-sm ${theme === "dark" ? "border-gray-700 text-gray-300" : "border-gray-300 text-gray-700"}`}>
            <UploadCloud className="w-4 h-4" />
            {file ? file.name : "Choose a CSV (prompt, allow/block) or compliance PDF"}
            <input type="file" accept=".csv,.pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
          <button type="submit" disabled={uploading || !file} className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 disabled:opacity-50 flex items-center gap-2 text-sm">
            {uploading && <Loader2 className="w-4 h-4 animate-spin" />} Upload
          </button>
        </div>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : packs.length === 0 ? (
          <p className="text-gray-500">No policy packs uploaded yet.</p>
        ) : (
          packs.map((p) => (
            <div key={p.pack_id} className={cardClass(theme)}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <Globe className="w-5 h-5 text-purple-500" />
                  </div>
                  <div>
                    <h3 className={`font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>{p.display_name}</h3>
                    <p className="text-xs text-gray-500">{p.country_code || p.pack_id}</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${p.enabled ? "bg-green-500/20 text-green-500" : "bg-gray-500/20 text-gray-500"}`}>
                  {p.enabled ? "ENABLED" : "DISABLED"}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                <span>{p.total_vectors} vectors</span>
                <span>{p.block_entries} block rules</span>
                <span>{p.allow_entries} allow rules</span>
              </div>
              <button onClick={() => handleToggle(p.pack_id, p.enabled)}
                className={`w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium border ${theme === "dark" ? "border-gray-700 hover:bg-gray-800 text-gray-300" : "border-gray-300 hover:bg-gray-100 text-gray-700"}`}>
                <Power className="w-3 h-3" /> {p.enabled ? "Disable" : "Enable"}
              </button>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
};
