import { ArrowRight, ChevronRight, LockOpen } from 'lucide-react'
import { useNavigate } from 'react-router'
import { markWelcomed } from '../welcomed.js'

/** The first screen: a headline, an illustration, and "Get started". */
export default function Welcome() {
  const navigate = useNavigate()

  function start() {
    markWelcomed()
    navigate('/dashboard')
  }

  return (
    <main className="welcome">
      <WelcomeArt />
      <div className="welcome-text">
        <h1>
          <b>Take control</b> of your finances today!
        </h1>
        <p>Track what comes in and what goes out, set a limit for each category, and see where your money goes every month.</p>
      </div>
      <button type="button" className="start-button" onClick={start}>
        <span className="start-button-knob" aria-hidden="true">
          <ArrowRight size={22} />
        </span>
        <span className="start-button-label">Get started</span>
        <span className="start-button-chevrons" aria-hidden="true">
          <ChevronRight size={16} />
          <ChevronRight size={16} />
          <ChevronRight size={16} />
        </span>
        <span className="start-button-lock" aria-hidden="true">
          <LockOpen size={18} />
        </span>
      </button>
    </main>
  )
}

/** A tilted budget card with a ring and bars, a stack of coins, and a "+$" bubble. Decoration only. */
function WelcomeArt() {
  return (
    <svg className="welcome-art" viewBox="0 0 340 300" aria-hidden="true">
      <defs>
        <radialGradient id="glow" cx="50%" cy="55%" r="50%">
          <stop offset="0%" stopColor="#2c3b3a" />
          <stop offset="100%" stopColor="#151718" />
        </radialGradient>
        <linearGradient id="coin" x1="0" x2="1">
          <stop offset="0%" stopColor="#f6c445" />
          <stop offset="100%" stopColor="#d99a12" />
        </linearGradient>
      </defs>
      <circle cx="170" cy="150" r="200" fill="none" stroke="#3a4a48" strokeWidth="1" opacity="0.6" />
      <circle cx="40" cy="20" r="150" fill="none" stroke="#3a4a48" strokeWidth="1" opacity="0.5" />
      <ellipse cx="175" cy="175" rx="150" ry="100" fill="url(#glow)" />

      <g transform="rotate(-8 175 150)">
        <rect x="70" y="78" width="200" height="140" rx="24" fill="#232327" stroke="#ffffff" strokeOpacity="0.08" />
        <circle cx="122" cy="148" r="30" fill="none" stroke="#3a3157" strokeWidth="13" />
        <circle cx="122" cy="148" r="30" fill="none" stroke="#8f75f5" strokeWidth="13" strokeLinecap="round" strokeDasharray="128 189" transform="rotate(-90 122 148)" />
        <rect x="172" y="112" width="74" height="9" rx="4.5" fill="#34343a" />
        <rect x="172" y="112" width="56" height="9" rx="4.5" fill="#1a9cbd" />
        <rect x="172" y="136" width="74" height="9" rx="4.5" fill="#34343a" />
        <rect x="172" y="136" width="34" height="9" rx="4.5" fill="#d9692b" />
        <rect x="172" y="160" width="74" height="9" rx="4.5" fill="#34343a" />
        <rect x="172" y="160" width="64" height="9" rx="4.5" fill="#1fa37a" />
        <rect x="172" y="184" width="44" height="7" rx="3.5" fill="#f4f4f5" opacity="0.25" />
      </g>

      <g>
        {[0, 1, 2, 3].map((i) => (
          <g key={i} transform={`translate(0 ${-i * 11})`}>
            <ellipse cx="268" cy="240" rx="34" ry="11" fill="#b37c0b" />
            <rect x="234" y="229" width="68" height="11" fill="#b37c0b" />
            <ellipse cx="268" cy="229" rx="34" ry="11" fill="url(#coin)" />
          </g>
        ))}
        <text x="268" y="201" textAnchor="middle" fontSize="13" fontWeight="700" fill="#7a5408">$</text>
      </g>

      <g transform="translate(58 214)">
        <rect width="78" height="34" rx="17" fill="#8f75f5" />
        <text x="39" y="22" textAnchor="middle" fontSize="15" fontWeight="700" fill="#0b0b0b">+$240</text>
      </g>
    </svg>
  )
}
