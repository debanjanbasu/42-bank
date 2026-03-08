import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import { Text, ActivityIndicator, IconButton } from 'react-native-paper';
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';
import { API_URL } from '@/config/env';
import { Transaction } from '@/types';

export default function TransactionsScreen() {
  const { user } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_URL}/api/transactions`, {
        headers: {
          Authorization: `Bearer ${await getStoredToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }

      const data = await response.json();
      setTransactions(data.transactions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const renderTransaction = ({ item }: { item: Transaction }) => {
    const isSent = item.sender === user?.username;
    const amount = isSent ? -item.amount : item.amount;
    const otherParty = isSent ? item.recipient : item.sender;

    return (
      <View style={styles.transactionItem}>
        <View style={styles.transactionIcon}>
          <IconButton
            icon={isSent ? 'arrow-up-circle' : 'arrow-down-circle'}
            size={32}
            iconColor={isSent ? darkTheme.colors.error : darkTheme.colors.success}
          />
        </View>
        <View style={styles.transactionDetails}>
          <Text style={styles.transactionDescription}>
            {otherParty || 'Unknown'}
          </Text>
          <Text style={styles.transactionDate}>
            {new Date(item.timestamp).toLocaleDateString()}
          </Text>
        </View>
        <View style={styles.transactionAmount}>
          <Text
            style={[
              styles.amountText,
              { color: isSent ? darkTheme.colors.error : darkTheme.colors.success },
            ]}
          >
            {isSent ? '-' : '+'}${Math.abs(item.amount).toFixed(2)}
          </Text>
          <Text style={styles.statusText}>
            {item.status}
          </Text>
        </View>
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <IconButton icon="refresh" onPress={fetchTransactions} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={transactions}
        renderItem={renderTransaction}
        keyExtractor={(item) => item.id}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No transactions yet</Text>
          </View>
        }
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

async function getStoredToken(): Promise<string | null> {
  const { StorageService } = await import('@/services/StorageService');
  return StorageService.getToken();
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: darkTheme.colors.background,
  },
  listContent: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: darkTheme.colors.background,
  },
  transactionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: darkTheme.colors.surface,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  transactionIcon: {
    marginRight: 12,
  },
  transactionDetails: {
    flex: 1,
  },
  transactionDescription: {
    fontSize: 16,
    fontWeight: '500',
    color: darkTheme.colors.text,
  },
  transactionDate: {
    fontSize: 14,
    color: darkTheme.colors.textSecondary,
    marginTop: 2,
  },
  transactionAmount: {
    alignItems: 'flex-end',
  },
  amountText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  statusText: {
    fontSize: 12,
    color: darkTheme.colors.textSecondary,
    marginTop: 2,
    textTransform: 'capitalize',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: darkTheme.colors.background,
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
});
