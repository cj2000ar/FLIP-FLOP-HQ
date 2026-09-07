/**
 * FlipFlop HQ Design System
 * Extracted from 08_WEBSITE brand tokens
 * Legacy Lab Visual Retrofit V1
 */

export const colors = {
  // Canvas
  background: '#000000', // Pure black
  surface: '#090909', // Near-black panels

  // Brand green
  green: '#2a7d3c',
  greenInk: '#62b676', // Light variant for text
  greenHover: '#267036',
  greenSoft: '#0d1710',

  // Brand red
  red: '#dd281c',
  redInk: '#f14234', // Light variant for text
  redHover: '#c72419',
  redSoft: '#1e0c0b',

  // Supporting
  white: '#ffffff',
  coolGray: '#888888',
  amber: '#ffb800',
  blue: '#4a90ff',
  neutral: '#444444',
};

export const typography = {
  fonts: {
    brand: "'Geist', Arial, sans-serif",
    display: "'Manrope', Arial, sans-serif",
    mono: "'Geist Mono', monospace",
  },
  weights: {
    thin: 100,
    light: 200,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    heavy: 900,
  },
};

export const motion = {
  // Apple Store smooth easing
  easing: 'cubic-bezier(0.22, 1, 0.36, 1)',

  // Transition durations (ms)
  transitions: {
    fast: 80,
    normal: 160,
    slow: 220,
  },

  // Page changes
  pageChange: {
    duration: 280,
    easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
    offset: '8px', // 6-12px directional movement
  },

  // Panel interactions
  panel: {
    hover: {
      lift: '2px',
      duration: 160,
    },
    scale: 1.005,
  },

  // Button press
  button: {
    press: 80,
    release: 160,
    scale: 0.99,
  },
};

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
};

export const wordmark = {
  FLIP: colors.greenInk,
  FLOP: colors.redInk,
  H: colors.redInk,
  Q: colors.greenInk,
};
