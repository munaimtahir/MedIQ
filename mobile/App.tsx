/**Main app component with navigation.*/

import React, { useState, useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createStackNavigator } from "@react-navigation/stack";
import { LoginScreen } from "./src/screens/LoginScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { PackagesScreen } from "./src/screens/PackagesScreen";
import { OfflineAttemptScreen } from "./src/screens/OfflineAttemptScreen";
import { QueueStatusScreen } from "./src/screens/QueueStatusScreen";
import { SyncScreen } from "./src/screens/SyncScreen";
import { tokenStore } from "./src/auth/tokenStore";
import { initDatabase } from "./src/storage/db";

type RootStackParamList = {
  Login: undefined;
  Home: undefined;
  Packages: undefined;
  OfflineAttempt: undefined;
  QueueStatus: undefined;
  Sync: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Initialize database
      await initDatabase();

      // Check if we have a refresh token
      const refreshToken = await tokenStore.getRefreshToken();
      if (refreshToken) {
        // Try to refresh to validate token
        const newToken = await tokenStore.refreshTokens();
        if (newToken) {
          setIsAuthenticated(true);
        }
      }
    } catch (error) {
      console.error("App initialization error:", error);
    } finally {
      setInitializing(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    await tokenStore.clearTokens();
    setIsAuthenticated(false);
  };

  if (initializing) {
    return null; // Or a loading screen
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!isAuthenticated ? (
          <Stack.Screen name="Login">
            {(props) => (
              <LoginScreen {...props} onLoginSuccess={handleLoginSuccess} />
            )}
          </Stack.Screen>
        ) : (
          <>
            <Stack.Screen name="Home">
              {(props) => (
                <HomeScreen
                  {...props}
                  onNavigate={(screen) => props.navigation.navigate(screen as any)}
                  onLogout={handleLogout}
                />
              )}
            </Stack.Screen>
            <Stack.Screen name="Packages">
              {(props) => (
                <PackagesScreen
                  {...props}
                  onBack={() => props.navigation.goBack()}
                />
              )}
            </Stack.Screen>
            <Stack.Screen name="OfflineAttempt">
              {(props) => (
                <OfflineAttemptScreen
                  {...props}
                  onBack={() => props.navigation.goBack()}
                />
              )}
            </Stack.Screen>
            <Stack.Screen name="QueueStatus">
              {(props) => (
                <QueueStatusScreen
                  {...props}
                  onBack={() => props.navigation.goBack()}
                />
              )}
            </Stack.Screen>
            <Stack.Screen name="Sync">
              {(props) => (
                <SyncScreen
                  {...props}
                  onBack={() => props.navigation.goBack()}
                />
              )}
            </Stack.Screen>
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
