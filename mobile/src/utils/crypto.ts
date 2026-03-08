import * as Crypto from 'expo-crypto';

export async function generateDeviceId(): Promise<string> {
  const randomBytes = await Crypto.getRandomBytesAsync(16);
  return Array.from(randomBytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function generateRandomString(length: number = 32): Promise<string> {
  const bytes = await Crypto.getRandomBytesAsync(length);
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, length);
}

export async function sha256(data: string): Promise<string> {
  const digest = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    data
  );
  return digest;
}

export function createSigningPayload(
  type: 'SEND' | 'REQUEST',
  recipient: string,
  amount: number,
  timestamp: number,
  nonce: string
): string {
  return `${type}|${recipient}|${amount.toFixed(2)}|${timestamp}|${nonce}`;
}
