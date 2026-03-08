import React, { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { Text, TextInput, Button, Checkbox } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';

export default function RegisterScreen() {
  const router = useRouter();
  const { register, isLoading } = useAuth();
  const [username, setUsername] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    if (!username.trim()) {
      setError('Username is required');
      return;
    }

    if (username.length < 3) {
      setError('Username must be at least 3 characters');
      return;
    }

    if (!/^[a-z0-9_]+$/.test(username.trim().toLowerCase())) {
      setError('Username can only contain lowercase letters, numbers, and underscores');
      return;
    }

    if (!agreedToTerms) {
      setError('Please agree to the terms of service');
      return;
    }

    setError('');
    try {
      await register(username.trim().toLowerCase());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.logo}>42</Text>
            <Text style={styles.title}>BANK</Text>
            <Text style={styles.subtitle}>Create Your Account</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.info}>
              Your account will be secured with quantum-safe cryptography.
              Keys are generated and stored on your device.
            </Text>

            <TextInput
              label="Username"
              value={username}
              onChangeText={setUsername}
              mode="outlined"
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="lowercase letters, numbers, _"
              style={styles.input}
              theme={{ colors: { primary: darkTheme.colors.primary } }}
            />

            <View style={styles.checkboxContainer}>
              <Checkbox
                status={agreedToTerms ? 'checked' : 'unchecked'}
                onPress={() => setAgreedToTerms(!agreedToTerms)}
                color={darkTheme.colors.primary}
              />
              <Text style={styles.checkboxLabel}>
                I agree to the Terms of Service and Privacy Policy
              </Text>
            </View>

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <Button
              mode="contained"
              onPress={handleRegister}
              loading={isLoading}
              disabled={isLoading}
              style={styles.button}
            >
              Create Account
            </Button>

            <Button
              mode="text"
              onPress={() => router.back()}
              disabled={isLoading}
              style={styles.linkButton}
              textColor={darkTheme.colors.primary}
            >
              Already have an account? Login
            </Button>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: darkTheme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logo: {
    fontSize: 80,
    fontWeight: 'bold',
    color: darkTheme.colors.primary,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: darkTheme.colors.primary,
    marginTop: -10,
  },
  subtitle: {
    fontSize: 16,
    color: darkTheme.colors.textSecondary,
    marginTop: 8,
  },
  form: {
    gap: 16,
  },
  info: {
    fontSize: 14,
    color: darkTheme.colors.textSecondary,
    textAlign: 'center',
    marginBottom: 8,
  },
  input: {
    backgroundColor: darkTheme.colors.surface,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkboxLabel: {
    fontSize: 14,
    color: darkTheme.colors.text,
    flex: 1,
    marginLeft: 8,
  },
  button: {
    marginTop: 8,
    paddingVertical: 6,
  },
  linkButton: {
    marginTop: 8,
  },
  error: {
    color: darkTheme.colors.error,
    textAlign: 'center',
  },
});
