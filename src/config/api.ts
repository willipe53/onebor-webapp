/**
 * API Configuration Constants
 *
 * IMPORTANT: The only valid API URL for all stages is https://api.onebor.com/panda
 * This file serves as a single source of truth for API configuration.
 */

// The only valid API URL for all environments
export const API_BASE_URL = "https://api.onebor.com/panda";

// Development proxy path (used by Vite)
export const DEV_PROXY_PATH = "/api";

// Environment-specific API URL configuration
export const getApiUrl = () => {
  return import.meta.env.DEV ? DEV_PROXY_PATH : API_BASE_URL;
};

// Common API endpoints
export const API_ENDPOINTS = {
  // User management
  GET_USERS: "/get_users",
  UPDATE_USER: "/update_user",

  // Client groups
  GET_CLIENT_GROUPS: "/get_client_groups",
  UPDATE_CLIENT_GROUP: "/update_client_group",

  // Entities
  GET_ENTITIES: "/get_entities",
  UPDATE_ENTITY: "/update_entity",
  GET_ENTITY_COUNT: "/get_entity_count",

  // Entity types
  GET_ENTITY_TYPES: "/get_entity_types",
  UPDATE_ENTITY_TYPE: "/update_entity_type",

  // Transactions
  GET_TRANSACTIONS: "/get_transactions",
  UPDATE_TRANSACTION: "/update_transaction",

  // Transaction types
  GET_TRANSACTION_TYPES: "/get_transaction_types",
  UPDATE_TRANSACTION_TYPE: "/update_transaction_type",

  // Transaction statuses
  GET_TRANSACTION_STATUSES: "/get_transaction_statuses",
  UPDATE_TRANSACTION_STATUS: "/update_transaction_status",

  // Invitations
  GET_INVITATIONS: "/get_invitations",
  UPDATE_INVITATION: "/update_invitation",

  // Generic
  DELETE_RECORD: "/delete_record",
} as const;

// Validation function to ensure correct API URL usage
export const validateApiUrl = (url: string): boolean => {
  return url === API_BASE_URL || url === DEV_PROXY_PATH;
};

// Helper to log API URL usage (for debugging)
export const logApiUrl = (context: string, url: string) => {
  if (!validateApiUrl(url)) {
    console.warn(
      `⚠️ Invalid API URL in ${context}: ${url}. Should be ${API_BASE_URL}`
    );
  }
};
