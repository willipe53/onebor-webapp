import React, {
  useState,
  useMemo,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Autocomplete,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  Stack,
} from "@mui/material";
import { Add } from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import * as apiService from "../services/api";
import {
  prettyPrint,
  formatNumberForDisplay,
  parseFormattedNumber,
} from "../utils";
import EntityForm from "./EntityForm";

interface DynamicTransactionFormProps {
  editingTransaction?: apiService.Transaction;
  onClose?: () => void;
}

interface DynamicTransactionFormRef {
  handleDismissal: () => void;
}

interface TransactionSchema {
  $schema?: string;
  title: string;
  description?: string;
  type: string;
  properties: Record<string, any>;
  required: string[];
  additionalProperties: boolean;
  valid_instruments: string[];
  valid_contra_groups: string[];
}

interface FormData {
  portfolio_entity_id: string;
  instrument_entity_id: string;
  transaction_type_id: string;
  contra_entity_id: string;
  properties: Record<string, any>;
}

// Transaction status constants
const TRANSACTION_STATUS = {
  INCOMPLETE: 1,
  QUEUED: 2,
  PROCESSED: 3,
} as const;

const DynamicTransactionForm = forwardRef<
  DynamicTransactionFormRef,
  DynamicTransactionFormProps
>(({ editingTransaction, onClose }, ref) => {
  const { userId } = useAuth();
  const queryClient = useQueryClient();

  // Form state
  const [formData, setFormData] = useState<FormData>({
    portfolio_entity_id: "",
    instrument_entity_id: "",
    transaction_type_id: "",
    contra_entity_id: "",
    properties: {},
  });

  // Step tracking
  const [currentStep, setCurrentStep] = useState(0);
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);

  // Entity creation modals
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [showInstrumentModal, setShowInstrumentModal] = useState(false);
  const [showcontraModal, setShowcontraModal] = useState(false);

  // Auto-save and form dismissal tracking
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [formattedFields, setFormattedFields] = useState<Set<string>>(
    new Set()
  );

  // Get current user data
  const { data: currentUser } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
    select: (data) => data[0],
  });

  // Get all entities for the user
  const { data: entities, isLoading: entitiesLoading } = useQuery({
    queryKey: ["entities", currentUser?.user_id],
    queryFn: () =>
      apiService.queryEntities({
        user_id: currentUser!.user_id,
      }),
    enabled: !!currentUser?.user_id,
  });

  // Get entities by category for API-driven enums
  const { data: currencyEntities, isLoading: currencyLoading } = useQuery({
    queryKey: ["entities", currentUser?.user_id, "category", "Currency"],
    queryFn: () =>
      apiService.queryEntitiesByCategory(currentUser!.user_id, "Currency"),
    enabled: !!currentUser?.user_id,
  });

  // Get other common entity categories
  const {
    data: portfolioEntitiesByCategory,
    isLoading: portfolioCategoryLoading,
  } = useQuery({
    queryKey: ["entities", currentUser?.user_id, "category", "Portfolio"],
    queryFn: () =>
      apiService.queryEntitiesByCategory(currentUser!.user_id, "Portfolio"),
    enabled: !!currentUser?.user_id,
  });

  const {
    data: instrumentEntitiesByCategory,
    isLoading: instrumentCategoryLoading,
  } = useQuery({
    queryKey: ["entities", currentUser?.user_id, "category", "Instrument"],
    queryFn: () =>
      apiService.queryEntitiesByCategory(currentUser!.user_id, "Instrument"),
    enabled: !!currentUser?.user_id,
  });

  // Get entity types
  const { data: entityTypes } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => apiService.queryEntityTypes({}),
  });

  // Get transaction types
  const { data: transactionTypes } = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => apiService.queryTransactionTypes({}),
  });

  // Initialize form data when editing an existing transaction
  React.useEffect(() => {
    if (editingTransaction) {
      // Debug: Check the size of the editing transaction data
      const transactionSize = JSON.stringify(editingTransaction).length;
      if (transactionSize > 10000) {
        // If larger than 10KB
        console.warn(
          `Large editing transaction detected: ${transactionSize} bytes`
        );
        console.log(
          "Editing transaction properties:",
          editingTransaction.properties
        );
      }

      // Safely parse properties - handle both string and object cases
      let parsedProperties = {};
      if (editingTransaction.properties) {
        if (typeof editingTransaction.properties === "string") {
          try {
            parsedProperties = JSON.parse(editingTransaction.properties);
          } catch (e) {
            console.warn("Failed to parse properties JSON:", e);
            parsedProperties = {};
          }
        } else if (typeof editingTransaction.properties === "object") {
          // Check if it's a corrupted object (has numeric keys)
          const keys = Object.keys(editingTransaction.properties);
          const hasNumericKeys = keys.some((key) => !isNaN(parseInt(key)));

          if (hasNumericKeys) {
            console.warn(
              "Detected corrupted properties object with numeric keys, resetting to empty"
            );
            parsedProperties = {};
          } else {
            parsedProperties = editingTransaction.properties;
          }
        }

        // Additional cleanup: Remove any remaining corrupted data
        if (parsedProperties && typeof parsedProperties === "object") {
          const cleanedProperties: any = {};
          Object.keys(parsedProperties).forEach((key) => {
            const value = parsedProperties[key];
            // Only keep properties with non-numeric keys and simple values
            if (
              isNaN(parseInt(key)) &&
              key.length > 1 &&
              (typeof value === "string" ||
                typeof value === "number" ||
                typeof value === "boolean")
            ) {
              cleanedProperties[key] = value;
            }
          });
          parsedProperties = cleanedProperties;
          console.log("🧹 Cleaned parsed properties:", parsedProperties);
        }
      }

      setFormData({
        portfolio_entity_id: editingTransaction.portfolio_entity_id.toString(),
        instrument_entity_id:
          editingTransaction.instrument_entity_id.toString(),
        transaction_type_id: editingTransaction.transaction_type_id.toString(),
        contra_entity_id: editingTransaction.contra_entity_id?.toString() || "",
        properties: parsedProperties,
      });
      // Mark as having unsaved changes when editing an existing transaction
      setHasUnsavedChanges(true);
    }
  }, [editingTransaction]);

  // Calculate current step when editing an existing transaction
  React.useEffect(() => {
    if (editingTransaction) {
      // Determine the appropriate step based on what's already filled
      const hasPortfolio = !!formData.portfolio_entity_id;
      const hasInstrument = !!formData.instrument_entity_id;
      const hasTransactionType = !!formData.transaction_type_id;
      const hasContra = !!formData.contra_entity_id;

      if (!hasPortfolio) {
        setCurrentStep(1); // Portfolio selection
      } else if (!hasInstrument) {
        setCurrentStep(2); // Instrument selection
      } else if (!hasTransactionType) {
        setCurrentStep(3); // Transaction type selection
      } else {
        // Check if contra is required
        const selectedType = transactionTypes?.find(
          (t) =>
            t.transaction_type_id === parseInt(formData.transaction_type_id)
        );

        let isContraRequired = false;
        if (selectedType?.properties) {
          try {
            const schema =
              typeof selectedType.properties === "string"
                ? JSON.parse(selectedType.properties)
                : selectedType.properties;
            const validContraGroups = schema.valid_contra_groups || [];
            isContraRequired = validContraGroups.length > 0;
          } catch (error) {
            console.error("Error parsing transaction schema:", error);
          }
        }

        if (isContraRequired && !hasContra) {
          setCurrentStep(3); // Contra selection
        } else {
          setCurrentStep(4); // Properties (final step)
        }
      }
    }
  }, [editingTransaction, formData, transactionTypes]);

  // Filter entities by type
  const portfolioEntities = useMemo(() => {
    if (!entities || !entityTypes) return [];

    const portfolioType = entityTypes.find((et) => et.name === "Portfolio");
    if (!portfolioType) return [];

    return entities.filter(
      (entity) => entity.entity_type_id === portfolioType.entity_type_id
    );
  }, [entities, entityTypes]);

  // Get selected portfolio entity
  const selectedPortfolio = useMemo(() => {
    if (!formData.portfolio_entity_id || !portfolioEntities) return null;
    return portfolioEntities.find(
      (e) => e.entity_id.toString() === formData.portfolio_entity_id
    );
  }, [formData.portfolio_entity_id, portfolioEntities]);

  const instrumentEntities = useMemo(() => {
    if (!entities || !entityTypes) return [];

    const instrumentTypes = entityTypes.filter(
      (et) => et.entity_category === "Instrument"
    );
    const instrumentTypeIds = instrumentTypes.map((et) => et.entity_type_id);

    return entities.filter((entity) =>
      instrumentTypeIds.includes(entity.entity_type_id)
    );
  }, [entities, entityTypes]);

  // Get selected instrument entity
  const selectedInstrument = useMemo(() => {
    if (!formData.instrument_entity_id || !entities) return null;
    return entities.find(
      (e) => e.entity_id.toString() === formData.instrument_entity_id
    );
  }, [formData.instrument_entity_id, entities]);

  // Get selected transaction type
  const selectedTransactionType = useMemo(() => {
    if (!formData.transaction_type_id || !transactionTypes) return null;
    return transactionTypes.find(
      (tt) => tt.transaction_type_id.toString() === formData.transaction_type_id
    );
  }, [formData.transaction_type_id, transactionTypes]);

  // Parse transaction type schema
  const transactionSchema = useMemo((): TransactionSchema | null => {
    if (!selectedTransactionType?.properties) return null;

    try {
      const schema =
        typeof selectedTransactionType.properties === "string"
          ? JSON.parse(selectedTransactionType.properties)
          : selectedTransactionType.properties;
      return schema;
    } catch (error) {
      console.error("Error parsing transaction schema:", error);
      return null;
    }
  }, [selectedTransactionType]);

  // Filter transaction types based on selected instrument
  const validTransactionTypes = useMemo(() => {
    if (!transactionTypes || !selectedInstrument || !entityTypes) return [];

    const instrumentType = entityTypes.find(
      (et) => et.entity_type_id === selectedInstrument.entity_type_id
    );
    if (!instrumentType?.short_label) return [];

    return transactionTypes.filter((tt) => {
      try {
        const schema =
          typeof tt.properties === "string"
            ? JSON.parse(tt.properties)
            : tt.properties;
        return schema.valid_instruments?.includes(instrumentType.short_label);
      } catch {
        return false;
      }
    });
  }, [transactionTypes, selectedInstrument, entityTypes]);

  // Filter counterparties based on selected instrument
  const validCounterparties = useMemo(() => {
    if (!entities || !selectedInstrument || !entityTypes || !transactionSchema)
      return [];

    const instrumentType = entityTypes.find(
      (et) => et.entity_type_id === selectedInstrument.entity_type_id
    );
    if (!instrumentType?.short_label) return [];

    // Get valid contra group short labels from transaction schema
    const validContraGroups = transactionSchema.valid_contra_groups || [];

    // Find entity types that match the valid contra groups
    const validEntityTypes = entityTypes.filter((et) =>
      validContraGroups.includes(et.short_label || "")
    );
    const validEntityTypeIds = validEntityTypes.map((et) => et.entity_type_id);

    return entities.filter((entity) =>
      validEntityTypeIds.includes(entity.entity_type_id)
    );
  }, [entities, selectedInstrument, entityTypes, transactionSchema]);

  // Create/Update transaction mutation
  const mutation = useMutation({
    mutationFn: (data: apiService.CreateTransactionRequest) => {
      if (editingTransaction) {
        const updateData = {
          ...data,
          transaction_id: editingTransaction.transaction_id,
        };
        return apiService.updateTransaction(updateData);
      } else {
        return apiService.createTransaction(data);
      }
    },
    onSuccess: () => {
      setShowSuccessSnackbar(true);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      if (onClose) {
        setTimeout(() => onClose(), 1000);
      }
    },
  });

  // Delete transaction mutation
  const deleteMutation = useMutation({
    mutationFn: (transactionId: number) => {
      return apiService.deleteTransaction(transactionId);
    },
    onMutate: async (transactionId: number) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["transactions"] });

      // Snapshot the previous value
      const previousTransactions = queryClient.getQueriesData({
        queryKey: ["transactions"],
      });

      // Optimistically update the cache by removing the deleted transaction
      queryClient.setQueriesData({ queryKey: ["transactions"] }, (old: any) => {
        if (!old) return old;
        return old.filter(
          (transaction: any) => transaction.transaction_id !== transactionId
        );
      });

      // Return a context object with the snapshotted value
      return { previousTransactions };
    },
    onError: (err, transactionId, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousTransactions) {
        context.previousTransactions.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      console.error("Transaction deletion failed:", err);
    },
    onSuccess: () => {
      // Invalidate to ensure we have the latest data
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      if (onClose) {
        onClose();
      }
    },
  });

  // Handle form submission (Create Transaction button - saves as QUEUED)
  const handleSubmit = () => {
    if (!currentUser?.user_id) return;

    const submitData: apiService.CreateTransactionRequest = {
      user_id: currentUser.user_id,
      portfolio_entity_id: parseInt(formData.portfolio_entity_id),
      instrument_entity_id: parseInt(formData.instrument_entity_id),
      transaction_type_id: parseInt(formData.transaction_type_id),
      contra_entity_id: isContraRequired
        ? parseInt(formData.contra_entity_id)
        : 0, // Use 0 or a default value when not required
      properties: formData.properties,
      transaction_status_id: TRANSACTION_STATUS.QUEUED, // Explicitly set to QUEUED
    };

    mutation.mutate(submitData);
  };

  // Handle cancel (discard changes)
  const handleCancel = () => {
    if (onClose) {
      onClose();
    }
  };

  // Check if transaction is INCOMPLETE (can be deleted)
  const isIncompleteTransaction = useMemo(() => {
    return (
      editingTransaction?.transaction_status_id ===
      TRANSACTION_STATUS.INCOMPLETE
    );
  }, [editingTransaction?.transaction_status_id]);

  // Handle delete transaction
  const handleDelete = () => {
    if (editingTransaction?.transaction_id) {
      deleteMutation.mutate(editingTransaction.transaction_id);
    }
  };

  // Handle input changes
  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    // Mark that there are unsaved changes
    setHasUnsavedChanges(true);

    // Reset subsequent steps when earlier selections change
    if (field === "portfolio_entity_id") {
      setFormData((prev) => ({
        ...prev,
        instrument_entity_id: "",
        transaction_type_id: "",
        contra_entity_id: "",
        properties: {},
      }));
      setCurrentStep(1);
      setShowContraSelection(false); // Reset contra selection state
    } else if (field === "instrument_entity_id") {
      setFormData((prev) => ({
        ...prev,
        transaction_type_id: "",
        contra_entity_id: "",
        properties: {},
      }));
      setCurrentStep(2);
    } else if (field === "transaction_type_id") {
      setFormData((prev) => {
        const newData = {
          ...prev,
          contra_entity_id: "",
          properties: {},
        };

        // Find the selected transaction type to get its schema
        const selectedType = transactionTypes?.find(
          (t) => t.transaction_type_id === parseInt(value)
        );
        let shouldAutoSetContra = false;
        let isContraRequired = false;

        if (selectedType?.properties) {
          try {
            const schema =
              typeof selectedType.properties === "string"
                ? JSON.parse(selectedType.properties)
                : selectedType.properties;

            const validContraGroups = schema.valid_contra_groups || [];
            shouldAutoSetContra = validContraGroups.includes("P");
            isContraRequired = validContraGroups.length > 0;
          } catch (error) {
            console.error("Error parsing transaction schema:", error);
          }
        }

        // Auto-set contra to portfolio if required
        if (shouldAutoSetContra && prev.portfolio_entity_id) {
          newData.contra_entity_id = prev.portfolio_entity_id;
        }

        // Determine next step based on contra requirements
        setTimeout(() => {
          if (shouldAutoSetContra && prev.portfolio_entity_id) {
            // Contra is auto-set, skip to properties step
            setCurrentStep(4);
          } else if (isContraRequired) {
            // Contra is required but not auto-set, go to contra step
            setCurrentStep(3);
          } else {
            // Contra is not required, go to properties step
            setCurrentStep(4);
          }
        }, 0);

        return newData;
      });
      setShowContraSelection(false); // Reset contra selection state
    } else if (field === "contra_entity_id") {
      setCurrentStep(4);
    }
  };

  // Handle property changes
  const handlePropertyChange = (propertyName: string, value: any) => {
    // Debug: Log property changes for amount field
    if (propertyName === "amount") {
      console.log(
        `🔢 Amount field change: ${propertyName} = ${value} (type: ${typeof value})`
      );
    }

    setFormData((prev) => ({
      ...prev,
      properties: {
        ...prev.properties,
        [propertyName]: value,
      },
    }));
    // Mark that there are unsaved changes
    setHasUnsavedChanges(true);
  };

  // Handle entity creation success
  const handlePortfolioCreated = (newEntity: any) => {
    setFormData((prev) => ({
      ...prev,
      portfolio_entity_id: newEntity.entity_id.toString(),
    }));
    setShowPortfolioModal(false);
    setCurrentStep(1);
    // Refresh entities data
    queryClient.invalidateQueries({ queryKey: ["entities"] });
  };

  const handleInstrumentCreated = (newEntity: any) => {
    setFormData((prev) => ({
      ...prev,
      instrument_entity_id: newEntity.entity_id.toString(),
    }));
    setShowInstrumentModal(false);
    setCurrentStep(2);
    // Refresh entities data
    queryClient.invalidateQueries({ queryKey: ["entities"] });
  };

  const handlecontraCreated = (newEntity: any) => {
    setFormData((prev) => ({
      ...prev,
      contra_entity_id: newEntity.entity_id.toString(),
    }));
    setShowcontraModal(false);
    setCurrentStep(4);
    // Refresh entities data
    queryClient.invalidateQueries({ queryKey: ["entities"] });
  };

  // Check if contra step is required
  const isContraRequired = useMemo(() => {
    if (!transactionSchema) return true;
    const validContraGroups = transactionSchema.valid_contra_groups || [];
    return validContraGroups.length > 0;
  }, [transactionSchema]);

  // Check if contra should be auto-set to portfolio
  const isContraAutoSetToPortfolio = useMemo(() => {
    if (!transactionSchema) return false;
    const validContraGroups = transactionSchema.valid_contra_groups || [];
    return validContraGroups.includes("P");
  }, [transactionSchema]);

  // State to control whether user wants to change contra from auto-set portfolio
  const [showContraSelection, setShowContraSelection] = useState(false);

  // Auto-advance to properties step if contra is auto-set and we're on contra step
  React.useEffect(() => {
    if (
      currentStep === 3 &&
      isContraAutoSetToPortfolio &&
      formData.contra_entity_id &&
      formData.transaction_type_id
    ) {
      setCurrentStep(4);
    }
  }, [
    currentStep,
    isContraAutoSetToPortfolio,
    formData.contra_entity_id,
    formData.transaction_type_id,
  ]);

  // Check if form can be submitted
  const canSubmit = useMemo(() => {
    const baseRequirements =
      formData.portfolio_entity_id &&
      formData.instrument_entity_id &&
      formData.transaction_type_id &&
      transactionSchema &&
      transactionSchema.required?.every(
        (req) => formData.properties[req] !== undefined
      );

    // Only require contra_entity_id if contra step is required
    const contraRequirement = isContraRequired
      ? formData.contra_entity_id
      : true;

    return baseRequirements && contraRequirement;
  }, [formData, transactionSchema, isContraRequired]);

  // Handle form dismissal (clicking outside the form)
  const handleFormDismissal = useCallback(() => {
    // Check if we have the minimum required fields for saving as INCOMPLETE
    const hasMinimumFields =
      formData.portfolio_entity_id &&
      formData.instrument_entity_id &&
      formData.transaction_type_id;

    if (hasMinimumFields && hasUnsavedChanges) {
      if (editingTransaction) {
        // Update existing transaction
        const updateData: apiService.UpdateTransactionRequest = {
          transaction_id: editingTransaction.transaction_id,
          user_id: currentUser?.user_id || 0,
          portfolio_entity_id: parseInt(formData.portfolio_entity_id),
          instrument_entity_id: parseInt(formData.instrument_entity_id),
          transaction_type_id: parseInt(formData.transaction_type_id),
          contra_entity_id: isContraRequired
            ? parseInt(formData.contra_entity_id)
            : 0,
          properties: formData.properties,
          transaction_status_id: TRANSACTION_STATUS.INCOMPLETE,
        };

        // Debug: Check the size of the request data
        const requestSize = JSON.stringify(updateData).length;
        console.log("🔍 Update request properties:", formData.properties);
        console.log("🔍 Property keys:", Object.keys(formData.properties));
        console.log(
          "🔍 Property values sample:",
          Object.values(formData.properties).slice(0, 5)
        );

        // Check for corrupted properties (numeric keys indicate corruption)
        const propertyKeys = Object.keys(formData.properties);
        const hasNumericKeys = propertyKeys.some(
          (key) => !isNaN(parseInt(key))
        );

        console.log("🔍 Has numeric keys:", hasNumericKeys);
        console.log("🔍 Request size:", requestSize);

        if (hasNumericKeys) {
          console.error(
            "🚨 CORRUPTED PROPERTIES DETECTED! Resetting to empty object."
          );
          // Preserve any valid user input (like amount) that might have been entered
          const validProperties: any = {};
          Object.keys(formData.properties).forEach((key) => {
            const value = formData.properties[key];
            // Keep only simple values that aren't part of the corrupted string
            if (
              typeof value === "string" ||
              typeof value === "number" ||
              typeof value === "boolean"
            ) {
              // Check if this looks like a real property name (not a numeric index)
              if (isNaN(parseInt(key)) && key.length > 1) {
                validProperties[key] = value;
              }
            }
          });
          updateData.properties = validProperties;
          console.log("🔧 Preserved valid properties:", validProperties);
        } else if (requestSize > 10000) {
          // If larger than 10KB
          console.warn(`Large request detected: ${requestSize} bytes`);
          console.log("Properties object:", formData.properties);

          // Clean up properties to prevent 413 error
          const cleanedProperties = Object.keys(formData.properties).reduce(
            (acc, key) => {
              const value = formData.properties[key];
              // Only keep simple values (strings, numbers, booleans, null, undefined)
              if (
                typeof value === "string" ||
                typeof value === "number" ||
                typeof value === "boolean" ||
                value === null ||
                value === undefined
              ) {
                acc[key] = value;
              } else {
                console.warn(`Removing complex property: ${key}`, value);
              }
              return acc;
            },
            {} as any
          );

          updateData.properties = cleanedProperties;
          console.log("Cleaned properties:", cleanedProperties);
        }

        apiService
          .updateTransaction(updateData)
          .then(() => {
            queryClient.invalidateQueries({ queryKey: ["transactions"] });
            // Close the form after successful save
            if (onClose) {
              onClose();
            }
          })
          .catch((error) => {
            console.error("Failed to update transaction on dismissal:", error);
          });
      } else {
        // Create new transaction
        const submitData: apiService.CreateTransactionRequest = {
          user_id: currentUser?.user_id || 0,
          portfolio_entity_id: parseInt(formData.portfolio_entity_id),
          instrument_entity_id: parseInt(formData.instrument_entity_id),
          transaction_type_id: parseInt(formData.transaction_type_id),
          contra_entity_id: isContraRequired
            ? parseInt(formData.contra_entity_id)
            : 0,
          properties: formData.properties,
          transaction_status_id: TRANSACTION_STATUS.INCOMPLETE,
        };

        // Debug: Check the size of the request data
        const requestSize = JSON.stringify(submitData).length;
        console.log("🔍 Create request properties:", formData.properties);

        // Check for corrupted properties (numeric keys indicate corruption)
        const propertyKeys = Object.keys(formData.properties);
        const hasNumericKeys = propertyKeys.some(
          (key) => !isNaN(parseInt(key))
        );

        if (hasNumericKeys) {
          console.error(
            "🚨 CORRUPTED PROPERTIES DETECTED! Resetting to empty object."
          );
          // Preserve any valid user input (like amount) that might have been entered
          const validProperties: any = {};
          Object.keys(formData.properties).forEach((key) => {
            const value = formData.properties[key];
            // Keep only simple values that aren't part of the corrupted string
            if (
              typeof value === "string" ||
              typeof value === "number" ||
              typeof value === "boolean"
            ) {
              // Check if this looks like a real property name (not a numeric index)
              if (isNaN(parseInt(key)) && key.length > 1) {
                validProperties[key] = value;
              }
            }
          });
          submitData.properties = validProperties;
          console.log("🔧 Preserved valid properties:", validProperties);
        } else if (requestSize > 10000) {
          // If larger than 10KB
          console.warn(`Large request detected: ${requestSize} bytes`);
          console.log("Properties object:", formData.properties);

          // Clean up properties to prevent 413 error
          const cleanedProperties = Object.keys(formData.properties).reduce(
            (acc, key) => {
              const value = formData.properties[key];
              // Only keep simple values (strings, numbers, booleans, null, undefined)
              if (
                typeof value === "string" ||
                typeof value === "number" ||
                typeof value === "boolean" ||
                value === null ||
                value === undefined
              ) {
                acc[key] = value;
              } else {
                console.warn(`Removing complex property: ${key}`, value);
              }
              return acc;
            },
            {} as any
          );

          submitData.properties = cleanedProperties;
          console.log("Cleaned properties:", cleanedProperties);
        }

        apiService
          .createTransaction(submitData)
          .then(() => {
            queryClient.invalidateQueries({ queryKey: ["transactions"] });
            // Close the form after successful save
            if (onClose) {
              onClose();
            }
          })
          .catch((error) => {
            console.error(
              "Failed to auto-save transaction on dismissal:",
              error
            );
          });
      }

      setHasUnsavedChanges(false);
    } else {
      // If no minimum fields or no changes, just close the form
      if (onClose) {
        onClose();
      }
    }
  }, [
    formData,
    hasUnsavedChanges,
    currentUser?.user_id,
    isContraRequired,
    queryClient,
    onClose,
    editingTransaction,
  ]);

  // Expose dismissal handler to parent via ref
  useImperativeHandle(
    ref,
    () => ({
      handleDismissal: handleFormDismissal,
    }),
    [handleFormDismissal]
  );

  // Render property field based on schema
  const renderPropertyField = (propertyName: string, propertySchema: any) => {
    const value = formData.properties[propertyName] || "";
    const isRequired = transactionSchema?.required?.includes(propertyName);
    const displayLabel = prettyPrint(propertyName);

    if (propertySchema.type === "string" && propertySchema.format === "date") {
      return (
        <DatePicker
          key={propertyName}
          label={`${displayLabel}${isRequired ? " *" : ""}`}
          value={value ? new Date(value) : null}
          onChange={(date) =>
            handlePropertyChange(
              propertyName,
              date?.toISOString().split("T")[0] || ""
            )
          }
          slotProps={{
            textField: {
              fullWidth: true,
              required: isRequired,
            },
          }}
        />
      );
    }

    // Handle API-driven enum fields (x-enum-api extension)
    // Example: "currency_code": { "x-enum-api": ["get_entities", "entity_category", "Currency"], "type": "string" }
    // This will automatically populate the autocomplete with entities from the specified category
    if (propertySchema["x-enum-api"]) {
      const apiConfig = propertySchema["x-enum-api"];
      const [apiEndpoint, paramKey, paramValue] = apiConfig;

      if (apiEndpoint === "get_entities" && paramKey === "entity_category") {
        // Lookup entities and loading state by category
        const categoryLookup: Record<
          string,
          { entities: any[] | undefined; loading: boolean }
        > = {
          Currency: { entities: currencyEntities, loading: currencyLoading },
          Portfolio: {
            entities: portfolioEntitiesByCategory,
            loading: portfolioCategoryLoading,
          },
          Instrument: {
            entities: instrumentEntitiesByCategory,
            loading: instrumentCategoryLoading,
          },
        };

        const categoryData = categoryLookup[paramValue];

        if (categoryData) {
          return (
            <Autocomplete
              key={propertyName}
              options={categoryData.entities || []}
              getOptionLabel={(option) => option.name}
              value={
                categoryData.entities?.find(
                  (entity) => entity.name === value
                ) || null
              }
              onChange={(_, newValue) =>
                handlePropertyChange(propertyName, newValue?.name || "")
              }
              loading={categoryData.loading}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={`${displayLabel}${isRequired ? " *" : ""}`}
                  required={isRequired}
                  fullWidth
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {categoryData.loading ? (
                          <CircularProgress color="inherit" size={20} />
                        ) : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
            />
          );
        } else {
          // Fallback for unsupported categories
          return (
            <TextField
              key={propertyName}
              label={`${displayLabel}${isRequired ? " *" : ""}`}
              value={value || ""}
              onChange={(e) =>
                handlePropertyChange(propertyName, e.target.value)
              }
              required={isRequired}
              fullWidth
              helperText={`Category "${paramValue}" not yet supported for API-driven enums`}
            />
          );
        }
      }
    }

    // Handle static enum fields
    if (propertySchema.enum) {
      return (
        <Autocomplete
          key={propertyName}
          options={propertySchema.enum}
          value={value || ""}
          onChange={(_, newValue) =>
            handlePropertyChange(propertyName, newValue || "")
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label={`${displayLabel}${isRequired ? " *" : ""}`}
              required={isRequired}
              fullWidth
            />
          )}
        />
      );
    }

    // Handle number fields with comma formatting
    if (propertySchema.type === "number") {
      const rawValue = formData.properties[propertyName];
      const displayValue =
        formattedFields.has(propertyName) &&
        rawValue !== undefined &&
        rawValue !== ""
          ? formatNumberForDisplay(rawValue)
          : rawValue?.toString() || "";

      return (
        <TextField
          key={propertyName}
          label={`${displayLabel}${isRequired ? " *" : ""}`}
          value={displayValue}
          onChange={(e) => {
            const numericValue = parseFormattedNumber(e.target.value);
            handlePropertyChange(propertyName, numericValue);
            // Remove from formatted fields when user is typing
            setFormattedFields((prev) => {
              const newSet = new Set(prev);
              newSet.delete(propertyName);
              return newSet;
            });
          }}
          onBlur={(e) => {
            // Format the field with commas when user tabs out
            const numericValue = parseFormattedNumber(e.target.value);
            handlePropertyChange(propertyName, numericValue);
            // Mark this field as formatted to show commas
            setFormattedFields((prev) => {
              const newSet = new Set(prev).add(propertyName);
              return newSet;
            });
          }}
          required={isRequired}
          fullWidth
          type="text" // Use text type to allow commas
          inputProps={{
            inputMode: "numeric",
            pattern: "[0-9,]*\\.?[0-9]*", // Allow numbers, commas, and decimal points
          }}
        />
      );
    }

    return (
      <TextField
        key={propertyName}
        label={`${displayLabel}${isRequired ? " *" : ""}`}
        value={value}
        onChange={(e) => handlePropertyChange(propertyName, e.target.value)}
        required={isRequired}
        fullWidth
        type="text"
      />
    );
  };

  const isLoading = entitiesLoading || mutation.isPending;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ p: 3, maxWidth: 600, mx: "auto" }}>
        <Typography variant="h5" gutterBottom>
          {editingTransaction ? "Edit Transaction" : "Create Transaction"}
        </Typography>

        <Stepper activeStep={currentStep} sx={{ mb: 3 }}>
          <Step>
            <StepLabel>Portfolio</StepLabel>
          </Step>
          <Step>
            <StepLabel>Instrument</StepLabel>
          </Step>
          <Step>
            <StepLabel>Transaction Type</StepLabel>
          </Step>
          {isContraRequired && (
            <Step>
              <StepLabel>Contra</StepLabel>
            </Step>
          )}
          <Step>
            <StepLabel>Properties</StepLabel>
          </Step>
        </Stepper>

        {/* Step 1: Portfolio Selection */}
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              1. Select Portfolio
            </Typography>
            <Stack direction="row" spacing={2} alignItems="flex-start">
              <Autocomplete
                options={portfolioEntities || []}
                getOptionLabel={(option) => option.name}
                value={
                  portfolioEntities?.find(
                    (e) =>
                      e.entity_id.toString() === formData.portfolio_entity_id
                  ) || null
                }
                onChange={(_, newValue) =>
                  handleInputChange(
                    "portfolio_entity_id",
                    newValue?.entity_id.toString() || ""
                  )
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Portfolio *"
                    required
                    fullWidth
                  />
                )}
                disabled={isLoading}
                sx={{ flex: 1 }}
              />
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setShowPortfolioModal(true)}
                disabled={isLoading}
                sx={{ minWidth: "auto", px: 2 }}
              >
                Add New
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Step 2: Instrument Selection */}
        {formData.portfolio_entity_id && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                2. Select Instrument
              </Typography>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Autocomplete
                  options={instrumentEntities || []}
                  getOptionLabel={(option) => {
                    const entityType = entityTypes?.find(
                      (et) => et.entity_type_id === option.entity_type_id
                    );
                    return entityType
                      ? `${option.name} (${entityType.name})`
                      : option.name;
                  }}
                  value={
                    instrumentEntities?.find(
                      (e) =>
                        e.entity_id.toString() === formData.instrument_entity_id
                    ) || null
                  }
                  onChange={(_, newValue) =>
                    handleInputChange(
                      "instrument_entity_id",
                      newValue?.entity_id.toString() || ""
                    )
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Instrument *"
                      required
                      fullWidth
                    />
                  )}
                  disabled={isLoading}
                  sx={{ flex: 1 }}
                />
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => setShowInstrumentModal(true)}
                  disabled={isLoading}
                  sx={{ minWidth: "auto", px: 2 }}
                >
                  Add New
                </Button>
              </Stack>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Transaction Type Selection */}
        {formData.instrument_entity_id && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                3. Select Transaction Type
              </Typography>
              <Autocomplete
                options={validTransactionTypes || []}
                getOptionLabel={(option) => option.name}
                value={
                  validTransactionTypes?.find(
                    (tt) =>
                      tt.transaction_type_id.toString() ===
                      formData.transaction_type_id
                  ) || null
                }
                onChange={(_, newValue) =>
                  handleInputChange(
                    "transaction_type_id",
                    newValue?.transaction_type_id.toString() || ""
                  )
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Transaction Type *"
                    required
                    fullWidth
                  />
                )}
                disabled={isLoading}
              />
              {validTransactionTypes.length === 0 && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  No valid transaction types found for the selected instrument.
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 4: Contra Selection */}
        {formData.transaction_type_id && isContraRequired && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                4. Select Contra
              </Typography>

              {/* Show simplified UI when contra is auto-set to portfolio */}
              {isContraAutoSetToPortfolio && !showContraSelection ? (
                <Box>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    Currency amount will be reduced in{" "}
                    <strong>{selectedPortfolio?.name}</strong>.
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={() => setShowContraSelection(true)}
                    disabled={isLoading}
                  >
                    Change Contra
                  </Button>
                </Box>
              ) : (
                /* Show full contra selection UI */
                <Stack direction="row" spacing={2} alignItems="flex-start">
                  <Autocomplete
                    options={validCounterparties || []}
                    getOptionLabel={(option) => option.name}
                    value={
                      validCounterparties?.find(
                        (e) =>
                          e.entity_id.toString() === formData.contra_entity_id
                      ) || null
                    }
                    onChange={(_, newValue) =>
                      handleInputChange(
                        "contra_entity_id",
                        newValue?.entity_id.toString() || ""
                      )
                    }
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="contra *"
                        required
                        fullWidth
                      />
                    )}
                    disabled={isLoading}
                    sx={{ flex: 1 }}
                  />
                  <Button
                    variant="outlined"
                    startIcon={<Add />}
                    onClick={() => setShowcontraModal(true)}
                    disabled={isLoading}
                    sx={{ minWidth: "auto", px: 2 }}
                  >
                    Add New
                  </Button>
                </Stack>
              )}

              {validCounterparties.length === 0 &&
                !isContraAutoSetToPortfolio && (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    No valid counterparties found for the selected instrument
                    and transaction type.
                  </Alert>
                )}
            </CardContent>
          </Card>
        )}

        {/* Step 5: Dynamic Properties */}
        {formData.transaction_type_id &&
          transactionSchema &&
          (formData.contra_entity_id || !isContraRequired) && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {isContraRequired
                    ? "5. Transaction Properties"
                    : "4. Transaction Properties"}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2 }}
                >
                  {transactionSchema.description}
                </Typography>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {Object.entries(transactionSchema.properties || {}).map(
                    ([propertyName, propertySchema]) =>
                      renderPropertyField(propertyName, propertySchema)
                  )}
                </Box>
              </CardContent>
            </Card>
          )}

        {/* Action Buttons */}
        <Box sx={{ display: "flex", gap: 2, mt: 3 }}>
          {onClose && (
            <Button
              variant="outlined"
              onClick={handleCancel}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
          )}
          {onClose && (
            <Button
              variant="outlined"
              onClick={handleFormDismissal}
              disabled={mutation.isPending}
              color="secondary"
            >
              Save for Later
            </Button>
          )}
          {isIncompleteTransaction && (
            <Button
              variant="outlined"
              onClick={handleDelete}
              disabled={mutation.isPending || deleteMutation.isPending}
              color="error"
            >
              {deleteMutation.isPending ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Deleting...
                </>
              ) : (
                "Delete Transaction"
              )}
            </Button>
          )}
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!canSubmit || mutation.isPending}
            sx={{ ml: "auto" }}
          >
            {mutation.isPending ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                {editingTransaction ? "Updating..." : "Creating..."}
              </>
            ) : editingTransaction ? (
              "Update Transaction"
            ) : (
              "Create Transaction"
            )}
          </Button>
        </Box>

        {/* Success Snackbar */}
        {showSuccessSnackbar && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Transaction {editingTransaction ? "updated" : "created"}{" "}
            successfully!
          </Alert>
        )}

        {/* Portfolio Creation Modal */}
        {showPortfolioModal && (
          <Box
            sx={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1300,
            }}
          >
            <Box
              sx={{
                backgroundColor: "white",
                borderRadius: 2,
                p: 3,
                maxWidth: 800,
                maxHeight: "90vh",
                overflow: "auto",
                mx: 2,
                width: "100%",
                "& .MuiPaper-root": {
                  boxShadow: "none",
                  maxWidth: "none",
                },
                "& .MuiDialog-paper": {
                  maxWidth: "none",
                  margin: 0,
                },
              }}
            >
              <Typography variant="h6" gutterBottom>
                Create New Portfolio
              </Typography>
              <Box sx={{ maxHeight: "70vh", overflow: "auto" }}>
                <EntityForm
                  onClose={() => setShowPortfolioModal(false)}
                  onSuccess={handlePortfolioCreated}
                  defaultEntityType="Portfolio"
                  disableDialog={true}
                />
              </Box>
            </Box>
          </Box>
        )}

        {/* Instrument Creation Modal */}
        {showInstrumentModal && (
          <Box
            sx={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1300,
            }}
          >
            <Box
              sx={{
                backgroundColor: "white",
                borderRadius: 2,
                p: 3,
                maxWidth: 800,
                maxHeight: "90vh",
                overflow: "auto",
                mx: 2,
                width: "100%",
                "& .MuiPaper-root": {
                  boxShadow: "none",
                  maxWidth: "none",
                },
                "& .MuiDialog-paper": {
                  maxWidth: "none",
                  margin: 0,
                },
              }}
            >
              <Typography variant="h6" gutterBottom>
                Create New Instrument
              </Typography>
              <Box sx={{ maxHeight: "70vh", overflow: "auto" }}>
                <EntityForm
                  onClose={() => setShowInstrumentModal(false)}
                  onSuccess={handleInstrumentCreated}
                  allowedEntityTypes={instrumentEntities
                    .map((inst) => {
                      const entityType = entityTypes?.find(
                        (et) => et.entity_type_id === inst.entity_type_id
                      );
                      return entityType?.name || "";
                    })
                    .filter(Boolean)}
                  disableDialog={true}
                />
              </Box>
            </Box>
          </Box>
        )}

        {/* Contra Creation Modal */}
        {showcontraModal && isContraRequired && (
          <Box
            sx={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1300,
            }}
          >
            <Box
              sx={{
                backgroundColor: "white",
                borderRadius: 2,
                p: 3,
                maxWidth: 800,
                maxHeight: "90vh",
                overflow: "auto",
                mx: 2,
                width: "100%",
                "& .MuiPaper-root": {
                  boxShadow: "none",
                  maxWidth: "none",
                },
                "& .MuiDialog-paper": {
                  maxWidth: "none",
                  margin: 0,
                },
              }}
            >
              <Typography variant="h6" gutterBottom>
                Create New Contra
              </Typography>
              <Box sx={{ maxHeight: "70vh", overflow: "auto" }}>
                <EntityForm
                  onClose={() => setShowcontraModal(false)}
                  onSuccess={handlecontraCreated}
                  allowedEntityTypes={
                    transactionSchema?.valid_contra_groups
                      ? entityTypes
                          ?.filter((et) =>
                            transactionSchema.valid_contra_groups.includes(
                              et.short_label || ""
                            )
                          )
                          .map((et) => et.name) || []
                      : []
                  }
                  disableDialog={true}
                />
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </LocalizationProvider>
  );
});

DynamicTransactionForm.displayName = "DynamicTransactionForm";

export default DynamicTransactionForm;
