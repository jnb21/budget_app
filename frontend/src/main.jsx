import '@fontsource-variable/urbanist'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import './index.css'
import App from './App.jsx'
import AuthProvider from './AuthProvider.jsx'
import MonthProvider from './MonthProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <MonthProvider>
          <App />
        </MonthProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
