import React, { useState, useContext } from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, Share2, Settings, Eye, PlayCircle } from 'lucide-react';
import { ThemeContext } from '../context/ThemeContext';

export const ModelDetail = ({ onBack }) => {
  const { theme } = useContext(ThemeContext);
  const [activeTab, setActiveTab] = useState('playground');

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Eye },
    { id: 'playground', label: 'Playground', icon: PlayCircle },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  const MockPlayground = () => (
    <div className={`flex flex-col h-[600px] border rounded-lg overflow-hidden ${theme === 'dark' ? 'border-gray-800' : 'border-gray-200'}`}>
      <div className={`p-4 border-b flex justify-between items-center ${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-gray-50 border-gray-200'}`}>
         <div className="flex gap-2">
            <span className="px-2 py-1 bg-green-500/20 text-green-500 text-xs rounded font-mono">POST</span>
            <span className={`text-sm font-mono ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>/v1/inference/sentiment-v2</span>
         </div>
         <button className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 flex items-center gap-2">
            <PlayCircle className="w-3 h-3"/> Run
         </button>
      </div>
      <div className="flex-1 flex flex-col md:flex-row">
         {/* Input */}
         <div className={`flex-1 p-0 border-r ${theme === 'dark' ? 'border-gray-800' : 'border-gray-200'}`}>
            <div className={`p-2 text-xs font-semibold ${theme === 'dark' ? 'text-gray-500 bg-gray-900' : 'text-gray-500 bg-gray-100'}`}>INPUT (JSON)</div>
            <textarea 
               className={`w-full h-full p-4 font-mono text-sm resize-none focus:outline-none ${theme === 'dark' ? 'bg-gray-950 text-gray-300' : 'bg-white text-gray-800'}`}
               defaultValue={`{\n  "text": "The new product features are absolutely amazing and the UI is slick!"\n}`}
            />
         </div>
         {/* Output */}
         <div className="flex-1 p-0">
            <div className={`p-2 text-xs font-semibold ${theme === 'dark' ? 'text-gray-500 bg-gray-900' : 'text-gray-500 bg-gray-100'}`}>OUTPUT</div>
            <div className={`w-full h-full p-4 font-mono text-sm ${theme === 'dark' ? 'bg-gray-950 text-green-400' : 'bg-gray-50 text-green-700'}`}>
               <pre>{`{\n  "sentiment": "positive",\n  "confidence": 0.985,\n  "latency_ms": 24,\n  "tokens_used": 15\n}`}</pre>
            </div>
         </div>
      </div>
    </div>
  );

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
           <button onClick={onBack} className={`p-2 rounded-full ${theme === 'dark' ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'}`}>
              <ChevronRight className="w-5 h-5 rotate-180" />
           </button>
           <div>
             <div className="flex items-center gap-3">
               <h1 className={`text-3xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>sentiment-analysis-v2</h1>
               <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-500/20 text-green-500">Active</span>
             </div>
             <p className={`${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'} mt-1`}>NLP model for sentiment classification</p>
           </div>
        </div>
        <div className="flex gap-2">
          <button className={`p-2 rounded-lg ${theme === 'dark' ? 'hover:bg-gray-800 text-white' : 'hover:bg-gray-100 text-gray-900'} transition-colors`}>
            <Share2 className="w-5 h-5" />
          </button>
          <button className={`p-2 rounded-lg ${theme === 'dark' ? 'hover:bg-gray-800 text-white' : 'hover:bg-gray-100 text-gray-900'} transition-colors`}>
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className={`border-b ${theme === 'dark' ? 'border-gray-800' : 'border-gray-200'}`}>
        <div className="flex gap-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 flex items-center gap-2 text-sm font-medium transition-colors relative ${
                activeTab === tab.id 
                  ? (theme === 'dark' ? 'text-white' : 'text-blue-600') 
                  : 'text-gray-500 hover:text-gray-400'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {activeTab === tab.id && (
                <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="py-4">
        {activeTab === 'playground' && <MockPlayground />}
        {activeTab === 'overview' && (
           <div className={`p-8 text-center rounded-lg border ${theme === 'dark' ? 'border-gray-800 bg-gray-900/50 text-gray-400' : 'border-gray-200 bg-gray-50 text-gray-600'}`}>
              Overview content placeholder (Charts/Readme)
           </div>
        )}
        {activeTab === 'settings' && (
           <div className={`p-8 text-center rounded-lg border ${theme === 'dark' ? 'border-gray-800 bg-gray-900/50 text-gray-400' : 'border-gray-200 bg-gray-50 text-gray-600'}`}>
              Model Settings placeholder
           </div>
        )}
      </div>
    </motion.div>
  );
};