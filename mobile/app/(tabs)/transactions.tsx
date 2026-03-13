import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import { Text, ActivityIndicator, IconButton } from 'react-native-paper';
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';
import { Transaction } from '@/types';
import { APIClient } from '@/services/APIClient';
import { CacheService } from '@/services/CacheService';

export default function TransactionsScreen() {
  const { user } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    try {
      setError(null);
	const data = await APIClient.get<{ transactions: Transaction[] }>('/api/accounts/transactions');
      setTransactions(data.transactions ?? []);
      await CacheService.setTransactions(data.transactions ?? []); // update cache
    } catch (err) {
      // Network error — try cache
      const cached = await CacheService.getTransactions();
      if (cached) {
        setTransactions(cached);
        setError('Showing cached data (offline)');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load transactions');
      }
    } finally {
      setIsLoading(false);
    }
  }, []); // stable — APIClient has no external deps

  useEffect(() => {
    const loadWithCache = async () => {
      const cached = await CacheService.getTransactions();
      if (cached) {
        setTransactions(cached);
        setIsLoading(false);
      }
      fetchTransactions(); // still fetch fresh in background
    };
    loadWithCache();
  }, []); // no fetchTransactions dep — intentional

  const renderTransaction = ({ item }: { item: Transaction }) => {
    const isSent = item.sender === user?.username;
    const otherParty = isSent ? item.recipient : item.sender;

    return (
      <View
        style={styles.transactionItem}
        accessible={true}
        accessibilityLabel={`${isSent ? 'Sent to' : 'Received from'} ${otherParty ?? 'Unknown'}`}
        accessibilityHint={`Amount: $${Math.abs(item.amount).toFixed(2)}, Status: ${item.status}`}
      >
        <View style={styles.transactionIcon}>
          <IconButton
            icon={isSent ? 'arrow-up-circle' : 'arrow-down-circle'}
            size={32}
            iconColor={isSent ? darkTheme.colors.error : darkTheme.colors.success}
            accessibilityLabel={isSent ? 'Outgoing transaction' : 'Incoming transaction'}
          />
        </View>
			<View style={styles.transactionDetails}>
				<Text style={styles.transactionDescription}>
					{item.description || 'Transaction'}
				</Text>
				<Text style={styles.transactionParty}>
					{isSent ? `To: ${item.recipient}` : `From: ${item.sender}`}
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

  // Hard error with no cached data to show
  if (error && transactions.length === 0) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <IconButton
          icon="refresh"
          onPress={fetchTransactions}
          accessible={true}
          accessibilityLabel="Retry loading transactions"
          accessibilityHint="Tap to retry fetching your transactions"
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error ? (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>{error}</Text>
        </View>
      ) : null}
      <FlatList
        data={transactions}
        renderItem={renderTransaction}
        keyExtractor={(item) => item.id + item.timestamp}
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
	transactionParty: {
		fontSize: 14,
		color: darkTheme.colors.textSecondary,
		marginTop: 2,
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
  offlineBanner: {
    backgroundColor: darkTheme.colors.surfaceVariant,
    padding: 8,
    alignItems: 'center',
  },
  offlineBannerText: {
    color: darkTheme.colors.onSurfaceVariant,
    fontSize: 13,
  },
});

