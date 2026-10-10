/**
 * AuraRAG Brand Logo
 * Minimal futuristic "A" / aura symbol combined with subtle sound-wave and knowledge-ring concept.
 * Geometric, recognizable, premium, works at any size.
 */
export default function Logo({ size = 28, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="AuraRAG Logo"
    >
      <defs>
        <linearGradient id="auroraGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7C5CFF" />
          <stop offset="50%" stopColor="#4F8CFF" />
          <stop offset="100%" stopColor="#2DD4BF" />
        </linearGradient>
        <linearGradient id="auroraSubtle" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7C5CFF" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#2DD4BF" stopOpacity="0.25" />
        </linearGradient>
      </defs>

      {/* Subtle outer aura knowledge ring */}
      <circle
        cx="16"
        cy="16"
        r="14"
        stroke="url(#auroraSubtle)"
        strokeWidth="1.2"
        strokeDasharray="2 3"
      />

      {/* Futuristic geometric "A" structure */}
      <path
        d="M16 4.5L5.5 25.5H9.5L16 12.5L22.5 25.5H26.5L16 4.5Z"
        fill="url(#auroraGrad)"
      />

      {/* Central sound-wave / knowledge crossbar */}
      <path
        d="M11.5 20.5H20.5"
        stroke="#080A0F"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="20.5" r="1.5" fill="#2DD4BF" />
    </svg>
  );
}
