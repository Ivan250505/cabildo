interface Props {
  patternId: string
  variant?: 'wayuu' | 'zenu' | 'nasa'
}

export default function IndigenousDivider({ patternId, variant = 'wayuu' }: Props) {
  const patterns = {
    wayuu: (
      <pattern id={patternId} x="0" y="0" width="20" height="16" patternUnits="userSpaceOnUse">
        <rect x="0" y="6" width="4" height="4" fill="#C8922A" />
        <rect x="8" y="2" width="4" height="4" fill="#B22222" />
        <rect x="16" y="6" width="4" height="4" fill="#C8922A" />
        <rect x="4" y="10" width="4" height="4" fill="#1A3A5C" opacity=".5" />
        <rect x="12" y="10" width="4" height="4" fill="#1A3A5C" opacity=".5" />
      </pattern>
    ),
    zenu: (
      <pattern id={patternId} x="0" y="0" width="32" height="16" patternUnits="userSpaceOnUse">
        <polygon points="0,8 4,0 8,8 4,16" fill="#C8922A" opacity=".6" />
        <polygon points="16,8 20,0 24,8 20,16" fill="#B22222" opacity=".5" />
        <rect x="8" y="7" width="8" height="2" fill="#1A3A5C" opacity=".3" />
        <rect x="24" y="7" width="8" height="2" fill="#1A3A5C" opacity=".3" />
      </pattern>
    ),
    nasa: (
      <pattern id={patternId} x="0" y="0" width="24" height="16" patternUnits="userSpaceOnUse">
        <rect x="0" y="4" width="4" height="4" fill="#B22222" opacity=".55" />
        <rect x="4" y="0" width="4" height="4" fill="#C8922A" opacity=".65" />
        <rect x="8" y="4" width="4" height="4" fill="#1A3A5C" opacity=".4" />
        <rect x="12" y="8" width="4" height="4" fill="#C8922A" opacity=".65" />
        <rect x="16" y="4" width="4" height="4" fill="#B22222" opacity=".55" />
        <rect x="20" y="0" width="4" height="4" fill="#1A3A5C" opacity=".4" />
      </pattern>
    ),
  }

  return (
    <div className="indigenous-divider">
      <svg viewBox="0 0 800 16" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <defs>{patterns[variant]}</defs>
        <rect width="800" height="16" fill={`url(#${patternId})`} />
      </svg>
    </div>
  )
}
