import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, Alert, TextInput as RNTextInput } from 'react-native';
import { Text, Card, List, Switch, Divider, Button, Dialog, Portal, TextInput } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { useBiometric } from '@/hooks/useBiometric';
import { KeyManager } from '@/services/KeyManager';
import { darkTheme } from '@/utils/theme';

export default function SettingsScreen() {
const router = useRouter();
const { user, logout } = useAuth();
const { isAvailable, isEnrolled, biometricType, authenticate } = useBiometric();
const [biometricEnabled, setBiometricEnabled] = React.useState(true);
const [importDialogVisible, setImportDialogVisible] = useState(false);
const [importData, setImportData] = useState('');

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout? This will delete your keys from this device.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            try {
              await logout();
              router.replace('/(auth)/login');
            } catch (error) {
              Alert.alert('Error', 'Failed to logout. Please try again.');
            }
          },
        },
      ]
    );
  };

  const handleBiometricToggle = async (value: boolean) => {
    if (value) {
      const success = await authenticate('Enable biometric authentication');
      if (success) {
        setBiometricEnabled(true);
      }
    } else {
      setBiometricEnabled(false);
    }
  };

const handleKeyBackup = async () => {
Alert.alert(
'Key Backup',
'This feature will allow you to backup your keys to restore on another device. Coming soon!',
[{ text: 'OK' }]
);
};

const handleImportKeys = () => {
setImportDialogVisible(true);
};

const confirmImportKeys = async () => {
try {
const parsed = JSON.parse(importData);
if (!parsed.publicKey || !parsed.privateKey) {
Alert.alert('Invalid Keys', 'The import data is missing required fields.');
return;
}

// Store the keys
await KeyManager.importKeys(parsed.publicKey, parsed.privateKey);

Alert.alert(
'Success!',
'Keys imported successfully. You can now use this device for transactions.',
[
{
text: 'OK',
onPress: () => {
setImportDialogVisible(false);
setImportData('');
},
},
]
);
} catch (e) {
Alert.alert(
'Import Failed',
e instanceof Error ? e.message : 'Invalid JSON format. Please check your import data.'
);
}
};

  const handleDeleteKeys = async () => {
    Alert.alert(
      'Delete Keys',
      'This will permanently delete your cryptographic keys. You will need to register again. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            await KeyManager.deleteKeys();
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.userName}>{user?.username}</Text>
          <Text style={styles.userId}>ID: {user?.user_id?.slice(0, 8)}...</Text>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <List.Section>
          <List.Subheader>Security</List.Subheader>
          
          {isAvailable && isEnrolled && (
            <>
              <List.Item
                title={`${biometricType} Authentication`}
                description="Require biometric to sign transactions"
                left={(props) => <List.Icon {...props} icon="fingerprint" />}
                right={() => (
                  <Switch
                    value={biometricEnabled}
                    onValueChange={handleBiometricToggle}
                    color={darkTheme.colors.primary}
                    accessible={true}
                    accessibilityLabel={`${biometricType} authentication toggle`}
                    accessibilityHint={biometricEnabled ? 'Tap to disable biometric authentication' : 'Tap to enable biometric authentication'}
                  />
                )}
                accessible={true}
                accessibilityLabel={`${biometricType} Authentication`}
              />
              <Divider />
            </>
          )}

<List.Item
title="Import Keys"
description="Import keys from another device or backend"
left={(props) => <List.Icon {...props} icon="cloud-download" />}
onPress={handleImportKeys}
accessible={true}
accessibilityLabel="Import Keys"
accessibilityHint="Imports cryptographic keys from another device or backend"
/>
<Divider />

<List.Item
title="Backup Keys"
description="Export encrypted key backup"
left={(props) => <List.Icon {...props} icon="cloud-upload" />}
onPress={handleKeyBackup}
accessible={true}
accessibilityLabel="Backup Keys"
accessibilityHint="Exports an encrypted backup of your cryptographic keys"
/>
<Divider />

          <List.Item
            title="Delete Keys"
            description="Remove all keys from this device"
            left={(props) => <List.Icon {...props} icon="delete" color={darkTheme.colors.error} />}
            onPress={handleDeleteKeys}
            titleStyle={{ color: darkTheme.colors.error }}
            accessible={true}
            accessibilityLabel="Delete Keys"
            accessibilityHint="Permanently removes all cryptographic keys. You will need to register again."
          />
        </List.Section>
      </Card>

      <Card style={styles.card}>
        <List.Section>
          <List.Subheader>Information</List.Subheader>
          
          <List.Item
            title="About 42-Bank"
            description="Quantum-safe banking for everyone"
            left={(props) => <List.Icon {...props} icon="information" />}
          />
          <Divider />

          <List.Item
            title="Version"
            description="1.0.0"
            left={(props) => <List.Icon {...props} icon="tag" />}
          />
          <Divider />

          <List.Item
            title="Help & Support"
            description="Get help with 42-Bank"
            left={(props) => <List.Icon {...props} icon="help-circle" />}
            onPress={() => Alert.alert('Help', 'Contact support at support@42bank.com')}
            accessible={true}
            accessibilityLabel="Help and Support"
            accessibilityHint="Opens help and support information"
          />
        </List.Section>
      </Card>

      <Button
        mode="contained"
        onPress={handleLogout}
        style={styles.logoutButton}
        buttonColor={darkTheme.colors.error}
        accessible={true}
        accessibilityLabel="Logout"
        accessibilityHint="Logs you out and deletes your keys from this device"
      >
        Logout
      </Button>

<Text style={styles.footer}>
Secured with ML-DSA-44 Quantum-Safe Cryptography
</Text>

<Portal>
<Dialog visible={importDialogVisible} onDismiss={() => setImportDialogVisible(false)}>
<Dialog.Title>Import Keys</Dialog.Title>
<Dialog.Content>
<Text style={styles.dialogInfo}>
Paste the JSON data from your key export file:
</Text>
<TextInput
multiline
numberOfLines={6}
mode="outlined"
placeholder='{"publicKey": "...", "privateKey": "..."}'
value={importData}
onChangeText={setImportData}
style={styles.input}
/>
</Dialog.Content>
<Dialog.Actions>
<Button onPress={() => setImportDialogVisible(false)}>Cancel</Button>
<Button onPress={confirmImportKeys}>Import</Button>
</Dialog.Actions>
</Dialog>
</Portal>
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
  card: {
    marginBottom: 16,
    backgroundColor: darkTheme.colors.surface,
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: darkTheme.colors.text,
  },
  userId: {
    fontSize: 14,
    color: darkTheme.colors.textSecondary,
    marginTop: 4,
  },
  logoutButton: {
    marginTop: 16,
    marginBottom: 16,
  },
footer: {
textAlign: 'center',
color: darkTheme.colors.textSecondary,
fontSize: 12,
marginBottom: 32,
},
dialogInfo: {
fontSize: 14,
color: darkTheme.colors.textSecondary,
marginBottom: 8,
},
input: {
marginTop: 8,
minHeight: 100,
},
});
