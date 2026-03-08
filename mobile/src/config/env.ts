import Constants from 'expo-constants';

type Environment = 'development' | 'staging' | 'production';

interface EnvironmentConfig {
  API_URL: string;
  A2A_URL: string;
  ENABLE_DEBUGGING: boolean;
}

const ENVIRONMENTS: Record<Environment, EnvironmentConfig> = {
  development: {
    API_URL: 'http://localhost:8000',
    A2A_URL: 'http://localhost:8000',
    ENABLE_DEBUGGING: true,
  },
  staging: {
    API_URL: 'https://42bank-staging.azurewebsites.net',
    A2A_URL: 'https://42bank-staging.azurewebsites.net',
    ENABLE_DEBUGGING: true,
  },
  production: {
    API_URL: 'https://42bank.azurewebsites.net',
    A2A_URL: 'https://42bank.azurewebsites.net',
    ENABLE_DEBUGGING: false,
  },
};

const ENV: Environment = __DEV__ ? 'development' : 'production';
const baseConfig = ENVIRONMENTS[ENV];

export const getConfig = (): EnvironmentConfig => {
  const extra = Constants.expoConfig?.extra;
  return {
    API_URL: extra?.apiUrl || baseConfig.API_URL,
    A2A_URL: extra?.a2aUrl || baseConfig.A2A_URL,
    ENABLE_DEBUGGING: extra?.enableDebugging ?? baseConfig.ENABLE_DEBUGGING,
  };
};

export const API_URL = getConfig().API_URL;
export const A2A_URL = getConfig().A2A_URL;
export const ENABLE_DEBUGGING = getConfig().ENABLE_DEBUGGING;
