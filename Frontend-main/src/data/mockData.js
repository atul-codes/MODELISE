import { Box, Activity, GitBranch, DollarSign } from 'lucide-react';

export const dashboardStats = [
  { label: 'Total Models', value: '24', change: '+12%', trend: 'up', icon: Box },
  { label: 'API Calls', value: '1.2M', change: '+23%', trend: 'up', icon: Activity },
  { label: 'Active Versions', value: '67', change: '+5%', trend: 'up', icon: GitBranch },
  { label: 'Monthly Cost', value: '$1,234', change: '-8%', trend: 'down', icon: DollarSign }
];

export const modelData = [
  { id: 1, name: 'sentiment-analysis-v2', type: 'NLP', status: 'active', calls: '234K', latency: '45ms', visibility: 'public' },
  { id: 2, name: 'image-classifier-resnet', type: 'Vision', status: 'active', calls: '891K', latency: '120ms', visibility: 'private' },
  { id: 3, name: 'fraud-detection-xgboost', type: 'Tabular', status: 'deploying', calls: '12K', latency: '23ms', visibility: 'org' },
  { id: 4, name: 'speech-to-text-whisper', type: 'Audio', status: 'active', calls: '456K', latency: '340ms', visibility: 'public' }
];

export const chartData = [
  { name: 'Mon', calls: 4000, latency: 45 },
  { name: 'Tue', calls: 3000, latency: 52 },
  { name: 'Wed', calls: 5000, latency: 38 },
  { name: 'Thu', calls: 4500, latency: 43 },
  { name: 'Fri', calls: 6000, latency: 41 },
  { name: 'Sat', calls: 3500, latency: 48 },
  { name: 'Sun', calls: 4200, latency: 44 }
];