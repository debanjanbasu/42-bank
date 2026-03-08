import React, { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Text, TextInput, Button, ActivityIndicator } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';

export default function LoginScreen() {
  const router = useRouter();
  const { login, isLoading } = useAuth();
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!username.trim()) {
      setError('Username is required');
      return;
    }

    setError('');
    try {
      await login(username.trim().toLowerCase());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.logo}>42</Text>
          <Text style={styles.title}>BANK</Text>
          <Text style={styles.subtitle}>Quantum-Safe Banking</Text>
        </View>

        <View style={styles.form}>
          <TextInput
            label="Username"
            value={username}
            onChangeText={setUsername}
            mode="outlined"
            autoCapitalize="none"
            autoCorrect={false}
            style={styles.input}
            theme={{ colors: { primary: darkTheme.colors.primary } }}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Button
            mode="contained"
            onPress={handleLogin}
            loading={isLoading}
            disabled={isLoading}
            style={styles.button}
          >
            Login
          </Button>

          <Button
            mode="text"
            onPress={() => router.push('/register')}
            disabled={isLoading}
            style={styles.linkButton}
            textColor={darkTheme.colors.primary}
          >
            Don't have an account? Register
          </Button>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: darkTheme.colors.background,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
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
  input: {
    backgroundColor: darkTheme.colors.surface,
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
