/**
 * Utility functions for the application
 */

/**
 * Converts snake_case or camelCase strings to Pretty Case for display labels
 * Examples:
 * - "inception_date" -> "Inception Date"
 * - "legal_name" -> "Legal Name"
 * - "contactEmail" -> "Contact Email"
 * - "registration_number" -> "Registration Number"
 */
export const prettyPrint = (str: string): string => {
  if (!str) return "";

  // Handle camelCase by inserting spaces before capital letters
  const withSpaces = str.replace(/([a-z])([A-Z])/g, "$1 $2");

  // Handle snake_case by replacing underscores with spaces
  const withoutUnderscores = withSpaces.replace(/_/g, " ");

  // Capitalize first letter of each word
  return withoutUnderscores
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
};

/**
 * Validates if a string is a valid email address
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Formats a date object to YYYY-MM-DD string for date inputs
 */
export const formatDateForInput = (date: Date): string => {
  return date.toISOString().split("T")[0];
};

/**
 * Parses a date string (YYYY-MM-DD) to a Date object
 */
export const parseDateFromInput = (dateStr: string): Date | null => {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? null : date;
};

/**
 * Date/Time utilities for consistent timezone handling
 * - Server always stores dates in UTC
 * - UI always displays dates in user's local timezone
 * - UI always sends dates to server in UTC
 */

/**
 * Parse a date from the server (assumes UTC) and return a Date object
 */
export const parseServerDate = (dateString: string): Date => {
  // Ensure the date string is treated as UTC
  const utcString = dateString.includes("Z") ? dateString : dateString + "Z";
  return new Date(utcString);
};

/**
 * Format a date for display in the user's local timezone
 */
export const formatLocalDate = (date: Date): string => {
  return date.toLocaleString([], {
    timeZoneName: "short",
  });
};

/**
 * Format a date for display in the user's local timezone (short format)
 */
export const formatLocalDateShort = (date: Date): string => {
  const dateStr = date.toLocaleDateString();
  const timeStr = date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
  return `${dateStr} ${timeStr}`;
};

/**
 * Convert a local date to UTC string for sending to server
 */
export const toServerDate = (date: Date): string => {
  return date.toISOString();
};

/**
 * Get current time as UTC string for server
 */
export const nowAsServerDate = (): string => {
  return new Date().toISOString();
};

/**
 * JSON utilities for consistent handling of data that might be string or object
 */

/**
 * Safely parse JSON data that might already be an object or a JSON string
 * Used for handling database fields that store JSON as strings
 */
export const parseJsonField = (data: any): Record<string, any> => {
  if (!data) return {};

  if (typeof data === "object") {
    return data;
  }

  if (typeof data === "string") {
    try {
      return JSON.parse(data);
    } catch {
      return {};
    }
  }

  return {};
};

/**
 * Prepare JSON data for form editing
 * Returns both the parsed object and the JSON string representation
 */
export const prepareJsonForForm = (
  data: any
): {
  object: Record<string, any>;
  jsonString: string;
} => {
  const parsedObject = parseJsonField(data);
  return {
    object: parsedObject,
    jsonString: JSON.stringify(parsedObject, null, 2),
  };
};
