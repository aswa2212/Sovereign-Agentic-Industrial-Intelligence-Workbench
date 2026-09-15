import React from 'react';
import ReactDOM from 'react-dom/client';

// 1. Self-hosted typography (Air-gap offline guarantee: Zero CDN requests)
import '@fontsource/space-grotesk/400.css';
import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';

// 2. Core design tokens & Refinery Control Deck stylesheets
import './styles/tokens.css';
import './styles/workbench.css';

import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
