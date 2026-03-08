import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { darkTheme } from '@/utils/theme';

export default function NotFoundScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>404</Text>
      <Text style={styles.subtitle}>Page not found</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: darkTheme.colors.background,
  },
  title: {
    fontSize: 48,
    fontWeight: 'bold',
    color: darkTheme.colors.primary,
  },
  subtitle: {
    fontSize: 18,
    color: darkTheme.colors.textSecondary,
    marginTop: 8,
  },
});
