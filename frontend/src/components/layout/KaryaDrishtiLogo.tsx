import React from 'react';

export interface KaryaDrishtiLogoProps {
  variant?: 'login' | 'header' | 'compact' | 'mobile';
  height?: number;
  className?: string;
  showSubtitle?: boolean;
}

/**
 * Official KaryaDrishti Brand Logo Component
 *
 * Sizing requirements:
 * - Desktop header: ~44–56px high
 * - Login page brand: ~56–76px high
 * - Mobile header: ~38–46px high
 * Uses object-fit: contain to preserve aspect ratio without clipping or distortion.
 */
export const KaryaDrishtiLogo: React.FC<KaryaDrishtiLogoProps> = ({
  variant = 'header',
  height,
  className = '',
  showSubtitle = true,
}) => {
  const isLogin = variant === 'login';
  const isMobile = variant === 'mobile';
  const isCompact = variant === 'compact';

  // Sizing adhering to Phase 3 design guidelines
  const defaultHeight = isLogin ? 64 : isMobile ? 42 : isCompact ? 36 : 48;
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
      aria-label="KaryaDrishti — Labour market intelligence"
    >
      {/* Official KaryaDrishti Logo Asset */}
      <img
        src="/assets/karya-drishti-logo.png"
        alt="KaryaDrishti Emblem"
        style={{
          height: `${logoHeight}px`,
          width: 'auto',
          display: 'block',
          objectFit: 'contain',
          flexShrink: 0,
        }}
      />

      {/* Subtle vertical divider on login page matching Reference Image 1 */}
      {isLogin && (
        <div
          style={{
            width: '1px',
            height: '46px',
            backgroundColor: 'var(--color-border, #E7DED0)',
            margin: '0 2px',
          }}
          aria-hidden="true"
        />
      )}

      {/* Brand Typography */}
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <span
          style={{
            fontFamily: 'Lora, Georgia, serif',
            fontSize: isLogin ? '26px' : isMobile ? '18px' : '21px',
            fontWeight: 700,
            color: 'var(--color-navy, #142D3A)',
            lineHeight: 1.15,
            letterSpacing: '-0.01em',
          }}
        >
          KaryaDrishti
        </span>
        {showSubtitle && (
          <span
            style={{
              fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
              fontSize: isLogin ? '13px' : isMobile ? '10.5px' : '11.5px',
              color: 'var(--color-text-sec, #6F716E)',
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

// Backward-compatible alias for any legacy imports
export const LmisLogo = KaryaDrishtiLogo;
export default KaryaDrishtiLogo;
