import { MD3DarkTheme, MD3LightTheme } from 'react-native-paper';

export const darkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: '#00d9ff',
    primaryContainer: '#0a4a5a',
    onPrimary: '#1a1a2e',
    onPrimaryContainer: '#00d9ff',
    secondary: '#ff6b6b',
    secondaryContainer: '#5a2020',
    onSecondary: '#ffffff',
    onSecondaryContainer: '#ff6b6b',
    tertiary: '#a855f7',
    tertiaryContainer: '#3b1d5c',
    background: '#1a1a2e',
    surface: '#16213e',
    surfaceVariant: '#0f3460',
    surfaceDisabled: '#2a2a4e',
    outline: '#4a4a6e',
    outlineVariant: '#3a3a5e',
    text: '#ffffff',
    textSecondary: '#a0a0c0',
    error: '#ff4757',
    errorContainer: '#5a2020',
    success: '#2ed573',
    warning: '#ffa502',
    elevation: {
      level0: 'transparent',
      level1: '#1e1e38',
      level2: '#242442',
      level3: '#2a2a4e',
      level4: '#30305a',
      level5: '#363666',
    },
  },
};

export const lightTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#00a8cc',
    primaryContainer: '#b3e5f5',
    background: '#f5f5f5',
    surface: '#ffffff',
    text: '#1a1a2e',
  },
};

export type AppTheme = typeof darkTheme;
