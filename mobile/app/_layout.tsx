import { useEffect, useRef } from 'react';
import { Stack } from 'expo-router';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { KeyboardProvider } from 'react-native-keyboard-controller';
import { StatusBar } from 'expo-status-bar';
import * as Notifications from 'expo-notifications';
import { AuthProvider } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { NotificationService } from '@/services/NotificationService';

export default function RootLayout() {
  const notificationListener = useRef<Notifications.Subscription | undefined>(undefined);
  const responseListener = useRef<Notifications.Subscription | undefined>(undefined);

  useEffect(() => {
    notificationListener.current = NotificationService.addNotificationListener(
      (notification) => {
        console.log('Notification received:', notification);
      },
    );
    responseListener.current = NotificationService.addResponseListener(
      (response) => {
        console.log('Notification tapped:', response);
        // TODO: navigate to relevant screen based on notification data
      },
    );
    return () => {
      if (notificationListener.current) {
        NotificationService.removeSubscription(notificationListener.current);
      }
      if (responseListener.current) {
        NotificationService.removeSubscription(responseListener.current);
      }
    };
  }, []);

  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <KeyboardProvider>
          <SafeAreaProvider>
            <PaperProvider theme={darkTheme}>
              <AuthProvider>
                <StatusBar style="light" />
                <Stack
                  screenOptions={{
                    headerShown: false,
                    contentStyle: { backgroundColor: darkTheme.colors.background },
                    animation: 'slide_from_right',
                  }}
                >
                  <Stack.Screen name="(auth)" />
                  <Stack.Screen name="(tabs)" />
                  <Stack.Screen name="+not-found" />
                </Stack>
              </AuthProvider>
            </PaperProvider>
          </SafeAreaProvider>
        </KeyboardProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
}
