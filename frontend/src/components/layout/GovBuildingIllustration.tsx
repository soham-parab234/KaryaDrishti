import React from 'react';

interface GovBuildingIllustrationProps {
  variant?: 'login' | 'hero';
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Government Building Architectural Illustration
 * 
 * Accurately reproduces the neoclassical Indian secretariat / parliament building:
 * - Central classical dome with clerestory drum windows and spire
 * - Indian national tricolour flag fluttering atop the dome
 * - Stately colonnaded portico with pediment, balustrades and classical wings
 * - Warm terracotta/apricot/peach architectural tones
 * - Lush green tree clusters flanking on the right
 * - Sweeping terracotta terraced foreground curve
 * - Left column / obelisk accent
 */
export const GovBuildingIllustration: React.FC<GovBuildingIllustrationProps> = ({
  variant = 'login',
  className = '',
  style,
}) => {
  const isHero = variant === 'hero';

  return (
    <div
      className={`gov-building-illustration-container ${className}`}
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: isHero ? '540px' : '480px',
        height: isHero ? '230px' : '240px',
        overflow: 'hidden',
        borderRadius: isHero ? '0 20px 20px 0' : '0 0 36px 0',
        ...style,
      }}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 540 260"
        preserveAspectRatio="xMidYMid slice"
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      >
        <defs>
          {/* Sky background gradient */}
          <linearGradient id="skyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fdf1e4" stopOpacity={isHero ? "0" : "1"} />
            <stop offset="35%" stopColor="#fae2cf" stopOpacity={isHero ? "0.4" : "1"} />
            <stop offset="70%" stopColor="#f7d4bd" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#f4c4a6" stopOpacity="0.95" />
          </linearGradient>

          {/* Sun glow behind dome */}
          <radialGradient id="sunGlow" cx="50%" cy="40%" r="50%">
            <stop offset="0%" stopColor="#fff8f0" stopOpacity="0.9" />
            <stop offset="45%" stopColor="#fed7b2" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#f7c8a6" stopOpacity="0" />
          </radialGradient>

          {/* Dome gradient */}
          <linearGradient id="domeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#f7d5be" />
            <stop offset="100%" stopColor="#d98960" />
          </linearGradient>

          {/* Facade shadow gradient */}
          <linearGradient id="facadeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#fdeee0" />
            <stop offset="100%" stopColor="#df8e63" />
          </linearGradient>

          {/* Sweeping foreground ground gradient */}
          <linearGradient id="groundGrad" x1="0%" y1="0%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#f3b18a" />
            <stop offset="100%" stopColor="#d77042" />
          </linearGradient>
        </defs>

        {/* 1. Sky & Sun Atmosphere */}
        <rect width="540" height="260" fill="url(#skyGrad)" />
        <circle cx="280" cy="95" r="95" fill="url(#sunGlow)" />

        {/* 2. Left Obelisk / Classical Pillar Accent */}
        <g opacity="0.65">
          <polygon points="40,240 55,140 75,140 85,240" fill="#edd0bd" />
          <polygon points="55,140 65,130 75,140" fill="#debca6" />
          <rect x="36" y="240" width="54" height="15" fill="#debca6" rx="2" />
        </g>

        {/* 3. Main Government Building Classical Architecture */}
        <g id="building-architecture" transform="translate(110, 45)">
          {/* Base Stepped Podium */}
          <rect x="20" y="155" width="300" height="25" fill="#e89e74" rx="2" />
          <rect x="30" y="150" width="280" height="6" fill="#f4bca0" />
          <rect x="40" y="145" width="260" height="5" fill="#f9cbaf" />

          {/* Central Dome & Spire */}
          {/* Spire */}
          <line x1="170" y1="20" x2="170" y2="40" stroke="#b45b32" strokeWidth="2.5" />
          <circle cx="170" cy="20" r="3" fill="#d97444" />

          {/* Indian National Tricolour Flag */}
          <g transform="translate(170, 18)">
            {/* Flagpole top finial */}
            <circle cx="0" cy="0" r="1.5" fill="#b45309" />
            {/* Saffron Stripe */}
            <path d="M 0 1 Q 10 -1 18 2 L 18 5 Q 10 2 0 4 Z" fill="#ff9933" />
            {/* White Stripe with Ashoka Chakra */}
            <path d="M 0 4 Q 10 2 18 5 L 18 8 Q 10 5 0 7 Z" fill="#ffffff" />
            <circle cx="9" cy="5" r="1.2" fill="#000080" />
            {/* Green Stripe */}
            <path d="M 0 7 Q 10 5 18 8 L 18 11 Q 10 8 0 10 Z" fill="#138808" />
          </g>

          {/* Cupola Finial Base */}
          <rect x="165" y="38" width="10" height="4" fill="#cf774c" rx="1" />

          {/* Dome Curvature */}
          <path
            d="M 148 75 C 148 42, 192 42, 192 75 Z"
            fill="url(#domeGrad)"
          />
          {/* Dome ribs for architectural depth */}
          <path d="M 170 42 Q 170 58 170 75" stroke="#fce4d4" strokeWidth="1.5" fill="none" opacity="0.6" />
          <path d="M 158 50 Q 163 62 165 75" stroke="#ba653b" strokeWidth="1.2" fill="none" opacity="0.7" />
          <path d="M 182 50 Q 177 62 175 75" stroke="#fce4d4" strokeWidth="1.2" fill="none" opacity="0.7" />

          {/* Drum under Dome with clerestory arches */}
          <rect x="144" y="75" width="52" height="18" fill="#e89e75" />
          <rect x="141" y="73" width="58" height="3" fill="#fbd6bf" />
          <rect x="141" y="92" width="58" height="4" fill="#cf774c" />
          {/* Clerestory arched windows */}
          {[149, 157, 165, 173, 181].map((x) => (
            <path
              key={x}
              d={`M ${x} 88 L ${x} 82 Q ${x + 2.5} 78 ${x + 5} 82 L ${x + 5} 88 Z`}
              fill="#9a4a25"
              opacity="0.85"
            />
          ))}

          {/* Main Facade Long Wings (Left & Right) */}
          <rect x="25" y="95" width="290" height="52" fill="url(#facadeGrad)" />
          {/* Upper cornice and balustrade */}
          <rect x="20" y="93" width="300" height="4" fill="#fbd7c2" />
          <rect x="22" y="89" width="296" height="4" fill="#e1926b" />

          {/* Classical Columns along Left Wing */}
          {[35, 48, 61, 74, 87, 100, 113, 126].map((colX) => (
            <g key={colX}>
              <rect x={colX} y="96" width="4.5" height="48" fill="#fceadc" />
              <rect x={colX - 1} y="95" width="6.5" height="2" fill="#debca6" />
              <rect x={colX - 1} y="142" width="6.5" height="3" fill="#debca6" />
              {/* Window behind column */}
              <rect x={colX + 5} y="103" width="6" height="10" rx="1" fill="#ba6137" opacity="0.7" />
              <rect x={colX + 5} y="122" width="6" height="15" rx="1" fill="#ba6137" opacity="0.7" />
            </g>
          ))}

          {/* Central Classical Portico (Grand Entrance) */}
          <polygon points="135,93 170,80 205,93" fill="#f7caa7" />
          <polygon points="140,93 170,83 200,93" fill="#deb393" />
          <rect x="135" y="93" width="70" height="4" fill="#fce4d4" />
          {/* Stately Portico Columns */}
          {[140, 150, 160, 175, 185, 195].map((colX) => (
            <g key={colX}>
              <rect x={colX} y="97" width="5.5" height="48" fill="#ffffff" />
              <rect x={colX - 1} y="95" width="7.5" height="2.5" fill="#fcdac2" />
              <rect x={colX - 1} y="143" width="7.5" height="3.5" fill="#fcdac2" />
            </g>
          ))}
          {/* Grand Center Arched Portal */}
          <path d="M 162 145 L 162 120 Q 170 112 178 120 L 178 145 Z" fill="#8f3c18" />

          {/* Classical Columns along Right Wing */}
          {[212, 225, 238, 251, 264, 277, 290, 303].map((colX) => (
            <g key={colX}>
              <rect x={colX} y="96" width="4.5" height="48" fill="#fceadc" />
              <rect x={colX - 1} y="95" width="6.5" height="2" fill="#debca6" />
              <rect x={colX - 1} y="142" width="6.5" height="3" fill="#debca6" />
              {/* Window behind column */}
              <rect x={colX + 5} y="103" width="6" height="10" rx="1" fill="#ba6137" opacity="0.7" />
              <rect x={colX + 5} y="122" width="6" height="15" rx="1" fill="#ba6137" opacity="0.7" />
            </g>
          ))}
        </g>

        {/* 4. Lush Green Tree Clusters Flanking on the Right */}
        <g id="landscape-trees" transform="translate(420, 120)">
          {/* Back Tree layer */}
          <circle cx="50" cy="55" r="38" fill="#3a6048" />
          <circle cx="20" cy="65" r="30" fill="#446e53" />
          <circle cx="80" cy="70" r="32" fill="#345741" />

          {/* Mid Tree layer */}
          <circle cx="40" cy="70" r="32" fill="#4d7c5f" />
          <circle cx="10" cy="80" r="26" fill="#588b6c" />
          <circle cx="70" cy="82" r="28" fill="#426b52" />

          {/* Foreground Tree Highlights */}
          <circle cx="35" cy="85" r="24" fill="#5c9371" />
          <circle cx="65" cy="95" r="22" fill="#4d7c5f" />
        </g>

        {/* 5. Sweeping Terracotta Foreground Ramp / Hill */}
        <path
          d="M -20 260 L -20 215 Q 180 230 330 220 Q 420 215 560 180 L 560 260 Z"
          fill="url(#groundGrad)"
        />
        <path
          d="M 120 260 Q 280 250 440 235 Q 500 230 560 210 L 560 260 Z"
          fill="#c86438"
          opacity="0.5"
        />
      </svg>
    </div>
  );
};
