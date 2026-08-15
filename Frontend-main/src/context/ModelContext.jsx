import React, { createContext, useState } from "react";

export const ModelContext = createContext();

export const ModelProvider = ({ children }) => {
  const [models, setModels] = useState([]);

  const addModel = (model) => {
    setModels((prev) => [model, ...prev]);
  };

  const updateModel = (id, updates) => {
    setModels((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  };

  return (
    <ModelContext.Provider value={{ models, addModel, updateModel }}>
      {children}
    </ModelContext.Provider>
  );
};