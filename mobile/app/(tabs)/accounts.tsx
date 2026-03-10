import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, RefreshControl } from 'react-native';
import { Text, Card, ActivityIndicator, IconButton } from 'react-native-paper';
import { ScrollView } from 'react-native-gesture-handler';
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';
import { Account } from '@/types';
import { APIClient } from '@/services/APIClient';
import { CacheService } from '@/services/CacheService';

export default function AccountsScreen() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccounts = useCallback(async () => {
    try {
      setError(null);
      const data = await APIClient.get<{ accounts: Account[] }>('/api/accounts');
      setAccounts(data.accounts ?? []);
      await CacheService.setAccounts(data.accounts ?? []); // update cache
    } catch (err) {
      // Network error — try cache
      const cached = await CacheService.getAccounts();
      if (cached) {
        setAccounts(cached);
        setError('Showing cached data (offline)');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load accounts');
      }
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  }, []); // stable — APIClient has no external deps

  useEffect(() => {
    const loadWithCache = async () => {
      const cached = await CacheService.getAccounts();
      if (cached) {
        setAccounts(cached);
        setIsLoading(false);
      }
      fetchAccounts(); // still fetch fresh in background
    };
    loadWithCache();
  }, []); // no fetchAccounts dep — intentional

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchAccounts();
  }, [fetchAccounts]);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={darkTheme.colors.primary}
        />
      }
    >
      {error && accounts.length === 0 ? (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <IconButton
            icon="refresh"
            onPress={fetchAccounts}
            accessible={true}
            accessibilityLabel="Retry loading accounts"
            accessibilityHint="Tap to retry fetching your accounts"
          />
        </View>
      ) : accounts.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No accounts found</Text>
        </View>
      ) : (
        <>
          {error ? (
            <View style={styles.offlineBanner}>
              <Text style={styles.offlineBannerText}>{error}</Text>
            </View>
          ) : null}
          {accounts.map((account) => (
          <Card
            key={account.type + (account.account_number ?? '')}
            style={styles.card}
            accessible={true}
            accessibilityLabel={`${account.type} account`}
            accessibilityHint={`Balance: $${account.balance.toFixed(2)}`}
          >
            <Card.Content>
              <View style={styles.cardHeader}>
                <Text style={styles.accountType}>
                  {account.type.charAt(0).toUpperCase() + account.type.slice(1)} Account
                </Text>
                <IconButton
                  icon={account.type === 'checking' ? 'checkbook' : 'piggy-bank'}
                  size={24}
                  iconColor={darkTheme.colors.primary}
                  accessibilityLabel={`${account.type} account icon`}
                />
              </View>
              <Text style={styles.balance}>
                ${account.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </Text>
              <Text style={styles.accountNumber}>
                ••••{account.account_number?.slice(-4) || '****'}
              </Text>
            </Card.Content>
          </Card>
        ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: darkTheme.colors.background,
  },
  content: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: darkTheme.colors.background,
  },
  card: {
    marginBottom: 16,
    backgroundColor: darkTheme.colors.surface,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  accountType: {
    fontSize: 16,
    color: darkTheme.colors.textSecondary,
  },
  balance: {
    fontSize: 32,
    fontWeight: 'bold',
    color: darkTheme.colors.text,
    marginTop: 8,
  },
  accountNumber: {
    fontSize: 14,
    color: darkTheme.colors.textSecondary,
    marginTop: 4,
  },
  errorContainer: {
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: darkTheme.colors.error,
    textAlign: 'center',
    marginBottom: 10,
  },
  emptyContainer: {
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    color: darkTheme.colors.textSecondary,
    fontSize: 16,
  },
  offlineBanner: {
    backgroundColor: darkTheme.colors.surfaceVariant,
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    alignItems: 'center',
  },
  offlineBannerText: {
    color: darkTheme.colors.onSurfaceVariant,
    fontSize: 13,
  },
});

