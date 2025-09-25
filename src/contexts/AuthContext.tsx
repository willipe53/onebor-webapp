import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import {
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from "amazon-cognito-identity-js";
import { userPool } from "../config/cognito";
import * as apiService from "../services/api";

interface AuthContextType {
  user: CognitoUser | null;
  userEmail: string | null;
  userName: string | null;
  userId: string | null;
  dbUserId: number | null; // Database user_id
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  confirmSignup: (email: string, confirmationCode: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  confirmForgotPassword: (
    email: string,
    confirmationCode: string,
    newPassword: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<CognitoUser | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [dbUserId, setDbUserId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Helper function to fetch and store database user_id
  const fetchAndStoreDbUserId = async (cognitoSub: string) => {
    try {
      const users = await apiService.queryUsers({ sub: cognitoSub });
      if (users && users.length > 0) {
        const databaseUserId = users[0].user_id;
        setDbUserId(databaseUserId);
        // Store in session storage for API calls
        sessionStorage.setItem("dbUserId", databaseUserId.toString());
        console.log("✅ Database user_id fetched and stored:", databaseUserId);
      }
    } catch (error) {
      console.error("❌ Failed to fetch database user_id:", error);
    }
  };

  useEffect(() => {
    // Initialize dbUserId from session storage if available
    const storedDbUserId = sessionStorage.getItem("dbUserId");
    if (storedDbUserId) {
      setDbUserId(parseInt(storedDbUserId, 10));
    }

    // Check if user is already logged in
    const currentUser = userPool.getCurrentUser();
    if (currentUser) {
      currentUser.getSession((err: any, session: any) => {
        if (err) {
          setIsLoading(false);
          return;
        }
        if (session && session.isValid()) {
          const idToken = session.getIdToken();
          const payload = idToken.payload;
          setUser(currentUser);
          setUserEmail(payload.email);
          setUserName(
            payload.name ||
              payload.given_name ||
              payload.email?.split("@")[0] ||
              ""
          );
          setUserId(payload.sub);
          // Fetch database user_id
          fetchAndStoreDbUserId(payload.sub);
        }
        setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      const authenticationDetails = new AuthenticationDetails({
        Username: email,
        Password: password,
      });

      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (session) => {
          const idToken = session.getIdToken();
          const payload = idToken.payload;
          setUser(cognitoUser);
          setUserEmail(payload.email);
          setUserName(
            payload.name ||
              payload.given_name ||
              payload.email?.split("@")[0] ||
              ""
          );
          setUserId(payload.sub);
          // Fetch database user_id
          fetchAndStoreDbUserId(payload.sub);
          resolve();
        },
        onFailure: (err) => {
          // Dispatch custom event for error handling
          window.dispatchEvent(
            new CustomEvent("auth-error", {
              detail: { error: err },
            })
          );
          reject(err);
        },
      });
    });
  };

  const signup = async (email: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const attributeList = [
        new CognitoUserAttribute({
          Name: "email",
          Value: email,
        }),
      ];

      userPool.signUp(email, password, attributeList, [], (err, result) => {
        if (err) {
          // Dispatch custom event for error handling
          window.dispatchEvent(
            new CustomEvent("auth-error", {
              detail: { error: err },
            })
          );
          reject(err);
          return;
        }

        if (result?.user) {
          // User created successfully, but needs email confirmation
          resolve();
        }
      });
    });
  };

  const confirmSignup = async (
    email: string,
    confirmationCode: string
  ): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.confirmRegistration(confirmationCode, true, (err) => {
        if (err) {
          // Dispatch custom event for error handling
          window.dispatchEvent(
            new CustomEvent("auth-error", {
              detail: { error: err },
            })
          );
          reject(err);
          return;
        }

        // Confirmation successful
        resolve();
      });
    });
  };

  const forgotPassword = async (email: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.forgotPassword({
        onSuccess: () => {
          resolve();
        },
        onFailure: (err) => {
          // Dispatch custom event for error handling
          window.dispatchEvent(
            new CustomEvent("auth-error", {
              detail: { error: err },
            })
          );
          reject(err);
        },
      });
    });
  };

  const confirmForgotPassword = async (
    email: string,
    confirmationCode: string,
    newPassword: string
  ): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.confirmPassword(confirmationCode, newPassword, {
        onSuccess: () => {
          resolve();
        },
        onFailure: (err) => {
          // Dispatch custom event for error handling
          window.dispatchEvent(
            new CustomEvent("auth-error", {
              detail: { error: err },
            })
          );
          reject(err);
        },
      });
    });
  };

  const logout = () => {
    if (user) {
      user.signOut();
    }
    setUser(null);
    setUserEmail(null);
    setUserName(null);
    setUserId(null);
    setDbUserId(null);
    // Clear from session storage
    sessionStorage.removeItem("dbUserId");
  };

  const value: AuthContextType = {
    user,
    userEmail,
    userName,
    userId,
    dbUserId,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    confirmSignup,
    forgotPassword,
    confirmForgotPassword,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
