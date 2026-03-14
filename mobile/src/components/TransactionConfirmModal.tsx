import React, { useState } from 'react';
import { View, StyleSheet, Modal, Linking } from 'react-native';
import { Text, Button, ActivityIndicator, Surface, Divider } from 'react-native-paper';
import { darkTheme } from '@/utils/theme';
import { KeyManager } from '@/services/KeyManager';
import { authenticateForTransaction } from '@/hooks/useBiometric';
import { useAuth } from '@/contexts/AuthContext';

interface TransactionConfirmModalProps {
  visible: boolean;
  recipient: string;
  amount: number;
  note: string;
  onConfirm: (signature: string) => void;
  onCancel: () => void;
}

export function TransactionConfirmModal({
visible,
recipient,
amount,
note,
onConfirm,
onCancel,
}: TransactionConfirmModalProps) {
const [isSigning, setIsSigning] = useState(false);
const [error, setError] = useState<string | null>(null);
const { logout } = useAuth();

const handleConfirm = async () => {
setError(null);
setIsSigning(true);
try {
const authenticated = await authenticateForTransaction(
`Authorize transfer of $${amount.toFixed(2)} to ${recipient}`,
);
if (!authenticated) {
setError('Authentication failed. Please try again or use passcode.');
return;
}

const payload = `${recipient}:${amount}:${note}`;
const signature = await KeyManager.sign(payload);
onConfirm(signature);
} catch (e) {
const errorMessage = e instanceof Error ? e.message : 'Signing failed';
// Check if it's a missing key error and provide helpful message
if (errorMessage.includes('Private key not found')) {
setError('No signing key found for this account. You need to register a new account with key generation.');
} else {
setError(errorMessage);
}
} finally {
setIsSigning(false);
}
};

const handleLogoutAndReregister = async () => {
await logout();
};

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onCancel}
    >
      <View style={styles.overlay}>
        <Surface style={styles.card} elevation={5}>
          <Text variant="headlineSmall" style={styles.title}>
            Confirm Transfer
          </Text>
          <Divider style={styles.divider} />

          <View style={styles.row}>
            <Text variant="bodyMedium" style={styles.label}>To</Text>
            <Text variant="bodyLarge" style={styles.value}>{recipient}</Text>
          </View>
          <View style={styles.row}>
            <Text variant="bodyMedium" style={styles.label}>Amount</Text>
            <Text variant="headlineMedium" style={styles.amount}>
              ${amount.toFixed(2)}
            </Text>
          </View>
          {note ? (
            <View style={styles.row}>
              <Text variant="bodyMedium" style={styles.label}>Note</Text>
              <Text variant="bodyMedium" style={styles.value}>{note}</Text>
            </View>
          ) : null}

          <Divider style={styles.divider} />

          <Text variant="bodySmall" style={styles.securityNote}>
            🔐 This transaction will be signed with your ML-DSA-44 key
          </Text>

{error ? (
<View style={styles.errorContainer}>
<Text style={styles.error}>{error}</Text>
{error.includes('No signing key found') && (
<Button
mode="outlined"
onPress={handleLogoutAndReregister}
style={styles.logoutButton}
size="small"
>
Log Out & Register New Account
</Button>
)}
</View>
) : null}

          {isSigning ? (
            <ActivityIndicator style={styles.spinner} />
          ) : (
            <View style={styles.buttons}>
              <Button
                mode="outlined"
                onPress={onCancel}
                style={styles.cancelButton}
                accessibilityLabel="Cancel transaction"
              >
                Cancel
              </Button>
              <Button
                mode="contained"
                onPress={handleConfirm}
                style={styles.confirmButton}
                accessibilityLabel="Confirm and sign transaction"
              >
                Sign & Send
              </Button>
            </View>
          )}
        </Surface>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  card: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    backgroundColor: darkTheme.colors.surface,
  },
  title: { textAlign: 'center', marginBottom: 8, color: darkTheme.colors.onSurface },
  divider: { marginVertical: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  label: { color: darkTheme.colors.onSurfaceVariant },
  value: { color: darkTheme.colors.onSurface, flex: 1, textAlign: 'right' },
  amount: { color: darkTheme.colors.primary, fontWeight: 'bold' },
  securityNote: { color: darkTheme.colors.onSurfaceVariant, textAlign: 'center', marginBottom: 16 },
  error: { color: darkTheme.colors.error, textAlign: 'center', marginBottom: 12 },
errorContainer: { alignItems: 'center', marginBottom: 12 },
logoutButton: { marginTop: 8 },
  spinner: { marginVertical: 16 },
  buttons: { flexDirection: 'row', gap: 12, marginTop: 8 },
  cancelButton: { flex: 1 },
  confirmButton: { flex: 1 },
});
