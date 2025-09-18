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
