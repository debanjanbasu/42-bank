/**
 * Crypto polyfills for React Native
 * 
 * @noble/post-quantum requires Web Crypto API's getRandomValues
 * This polyfill provides it using expo-crypto
 */

import * as ExpoCrypto from 'expo-crypto';

// Polyfill crypto.getRandomValues for React Native
// This MUST be called before any noble-post-quantum operations
if (typeof global.crypto === 'undefined' || !global.crypto.getRandomValues) {
  global.crypto = {
    getRandomValues: <T extends Uint8Array>(buffer: T): T => {
      const randomBytes = ExpoCrypto.getRandomBytes(buffer.length);
      buffer.set(randomBytes);
      return buffer;
    },
  } as any;
}

// TypeScript declarations
declare global {
  var crypto: {
    getRandomValues: <T extends Uint8Array>(buffer: T) => T;
  };
}

export {};
