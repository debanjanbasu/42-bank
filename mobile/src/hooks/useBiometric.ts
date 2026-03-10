import { useState, useEffect, useCallback } from 'react';
import * as LocalAuthentication from 'expo-local-authentication';

export function useBiometric() {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [biometricType, setBiometricType] = useState<string>('');

  useEffect(() => {
    checkBiometricAvailability();
  }, []);

  const checkBiometricAvailability = async () => {
    const compatible = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    const type = await LocalAuthentication.supportedAuthenticationTypesAsync();

    setIsAvailable(compatible);
    setIsEnrolled(enrolled);

    if (type.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
      setBiometricType('Face ID');
    } else if (type.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
      setBiometricType('Fingerprint');
    } else if (type.includes(LocalAuthentication.AuthenticationType.IRIS)) {
      setBiometricType('Iris');
    } else {
      setBiometricType('Biometric');
    }
  };

  const authenticate = useCallback(
    async (promptMessage?: string): Promise<boolean> => {
      if (!isAvailable || !isEnrolled) {
        return false;
      }

      try {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: promptMessage || 'Authenticate to continue',
          cancelLabel: 'Cancel',
          disableDeviceFallback: true,
        });

        return result.success;
      } catch (error) {
        console.error('Biometric auth error:', error);
        return false;
      }
    },
    [isAvailable, isEnrolled]
  );

  return {
    isAvailable,
    isEnrolled,
    biometricType,
    authenticate,
  };
}

export async function authenticateForTransaction(description: string): Promise<boolean> {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  if (!compatible || !enrolled) return false;

  try {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: description,
      cancelLabel: 'Cancel',
      disableDeviceFallback: true,
    });
    return result.success;
  } catch {
    return false;
  }
}
