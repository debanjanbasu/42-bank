jest.mock('react-native-keychain', () => ({
  setGenericPassword: jest.fn().mockResolvedValue(true),
  getGenericPassword: jest.fn().mockResolvedValue({ username: 'key', password: 'value' }),
  resetGenericPassword: jest.fn().mockResolvedValue(true),
  ACCESSIBLE: { WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'AccessibleWhenUnlockedThisDeviceOnly' },
  AUTHENTICATION_TYPE: { BIOMETRICS: 'AuthenticationWithBiometrics' },
}));

jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn().mockResolvedValue(true),
  isEnrolledAsync: jest.fn().mockResolvedValue(true),
  authenticateAsync: jest.fn().mockResolvedValue({ success: true }),
  supportedAuthenticationTypesAsync: jest.fn().mockResolvedValue([1]),
  AuthenticationType: { FINGERPRINT: 1, FACIAL_RECOGNITION: 2, IRIS: 3 },
}));

jest.mock('@react-native-async-storage/async-storage', () => {
  return {
    getItem: jest.fn(async (key) => {
      return null;
    }),
    setItem: jest.fn(async (key, value) => {
      return;
    }),
    removeItem: jest.fn(async (key) => {
      return;
    }),
    clear: jest.fn(async () => {
      return;
    }),
    getAllKeys: jest.fn(async () => {
      return [];
    }),
    multiGet: jest.fn(async (keys) => {
      return keys.map(key => [key, null]);
    }),
    multiSet: jest.fn(async (keyValuePairs) => {
      return;
    }),
    multiRemove: jest.fn(async (keys) => {
      return;
    }),
  };
});
