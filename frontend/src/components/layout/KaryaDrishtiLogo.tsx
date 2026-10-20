import React from 'react';

interface KaryaDrishtiLogoProps {
  variant?: 'login' | 'header' | 'compact';
  height?: number;
  className?: string;
  showSubtitle?: boolean;
}

/**
 * Official KaryaDrishti Brand Logo Component
 * 
 * Uses the official logo asset from /logo.png, preserving 100% of the
 * aspect ratio, colors, emblem artwork, and Lora serif typography.
 */
export const KaryaDrishtiLogo: React.FC<KaryaDrishtiLogoProps> = ({
  variant = 'header',
  height,
  className = '',
  showSubtitle = true,
}) => {
  const isLogin = variant === 'login';
  const defaultHeight = isLogin ? 56 : variant === 'compact' ? 34 : 40;
  const logoHeight = height || defaultHeight;

  return (
    <div
      className={`karyadrishti-brand-group ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: isLogin ? '14px' : '10px',
        userSelect: 'none',
      }}
      role="banner"
      aria-label="KaryaDrishti — Labour Market Intelligence"
    >
      {/* Official KaryaDrishti logo asset */}
      <img
        src="/logo.png"
        alt="KaryaDrishti — Labour Market Intelligence Emblem"
        style={{
          height: `${logoHeight}px`,
          width: 'auto',
          display: 'block',
          objectFit: 'contain',
          flexShrink: 0,
        }}
      />

      {/* Vertical separator on login page matching Image 1 */}
      {isLogin && (
        <div
          style={{
            width: '1px',
            height: '42px',
            backgroundColor: '#d6d3d1',
            margin: '0 2px',
          }}
          aria-hidden="true"
        />
      )}

      {/* Official Typography Group */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <span
          style={{
            fontFamily: 'Lora, Georgia, serif',
            fontSize: isLogin ? '26px' : '20px',
            fontWeight: 700,
            color: '#1c1917',
            lineHeight: 1.15,
            letterSpacing: '-0.01em',
          }}
        >
          KaryaDrishti
        </span>
        {showSubtitle && (
          <span
            style={{
              fontFamily: 'Inter, system-ui, sans-serif',
              fontSize: isLogin ? '12.5px' : '11.5px',
              color: '#78716c',
              fontWeight: 400,
              letterSpacing: '0.01em',
              marginTop: '2px',
            }}
          >
            Labour market intelligence
          </span>
        )}
      </div>
    </div>
  );
};

// Also export as LmisLogo for backward compatibility with existing imports
export const LmisLogo = KaryaDrishtiLogo;
