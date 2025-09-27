import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
  Snackbar,
  Autocomplete,
} from "@mui/material";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import { apiService } from "../services/api";
// Define interfaces locally to avoid import issues
interface Transaction {
  transaction_id: number;
  portfolio_entity_id: number;
  contra_entity_id: number;
  instrument_entity_id: number;
  properties?: any;
  transaction_status_id: number;
  transaction_type_id: number;
  update_date?: string;
  updated_user_id?: number;
}

interface CreateTransactionRequest {
  portfolio_entity_id: number;
  contra_entity_id: number;
  instrument_entity_id: number;
  properties?: any;
  transaction_type_id: number;
  transaction_status_id?: number;
  user_id: number;
}

interface UpdateTransactionRequest extends CreateTransactionRequest {
  transaction_id?: number;
}
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-github";
import FormJsonToggle from "./FormJsonToggle";
import AuditTrail from "./AuditTrail";

interface TransactionFormProps {
  editingTransaction?: Transaction;
  onSuccess?: () => void;
  onClose?: () => void;
}

const TransactionForm: React.FC<TransactionFormProps> = ({
  editingTransaction,
  onSuccess,
  onClose,
}) => {
  const { dbUserId, userId } = useAuth();
  const queryClient = useQueryClient();

  // Debug logging
  console.log("🔍 TransactionForm - dbUserId:", dbUserId);

  // Fetch entities
  const {
    data: entities,
    isLoading: entitiesLoading,
    error: entitiesError,
  } = useQuery({
    queryKey: ["entities", dbUserId],
    queryFn: () => apiService.queryEntities({ user_id: dbUserId! }),
    enabled: !!dbUserId,
  });

  // Debug logging for entities
  console.log("🔍 TransactionForm - entities:", entities);
  console.log("🔍 TransactionForm - entitiesLoading:", entitiesLoading);
  console.log("🔍 TransactionForm - entitiesError:", entitiesError);

  // Fetch transaction types
  const { data: transactionTypes } = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => apiService.queryTransactionTypes({}),
  });

  // Fetch current user details for audit trail
  const { data: currentUserData } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
    select: (data) => data[0],
  });

  const [formData, setFormData] = useState({
    portfolio_entity_id: "",
    contra_entity_id: "",
    instrument_entity_id: "",
    transaction_type_id: "",
    transaction_status_id: "",
  });

  const [propertiesMode, setPropertiesMode] = useState<"form" | "json">("form");
  const [properties, setProperties] = useState("{}");
  const [jsonError, setJsonError] = useState("");
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);
  const [formProperties, setFormProperties] = useState<{
    [key: string]: string;
  }>({});
  const [initialFormState, setInitialFormState] = useState<{
    formData: typeof formData;
    properties: string;
    formProperties: { [key: string]: string };
  }>({ formData, properties: "{}", formProperties: {} });

  // Initialize form data
  useEffect(() => {
    if (editingTransaction) {
      const newFormData = {
        portfolio_entity_id: editingTransaction.portfolio_entity_id.toString(),
        contra_entity_id: editingTransaction.contra_entity_id.toString(),
        instrument_entity_id:
          editingTransaction.instrument_entity_id.toString(),
        transaction_type_id: editingTransaction.transaction_type_id.toString(),
        transaction_status_id:
          editingTransaction.transaction_status_id.toString(),
      };

      setFormData(newFormData);

      // Handle properties
      let propertiesString = "{}";
      let formProps: { [key: string]: string } = {};
      if (editingTransaction.properties) {
        try {
          propertiesString = JSON.stringify(
            editingTransaction.properties,
            null,
            2
          );
          // Convert properties to form format
          if (typeof editingTransaction.properties === "object") {
            formProps = Object.fromEntries(
              Object.entries(editingTransaction.properties).map(
                ([key, value]) => [
                  key,
                  typeof value === "string" ? value : JSON.stringify(value),
                ]
              )
            );
          }
        } catch (error) {
          console.error("Error parsing properties:", error);
          propertiesString = "{}";
        }
      }
      setProperties(propertiesString);
      setFormProperties(formProps);
      setInitialFormState({
        formData: newFormData,
        properties: propertiesString,
        formProperties: formProps,
      });
    } else {
      // Reset form for new transaction
      const newFormData = {
        portfolio_entity_id: "",
        contra_entity_id: "",
        instrument_entity_id: "",
        transaction_type_id: "",
        transaction_status_id: "",
      };
      setFormData(newFormData);
      setProperties("{}");
      setFormProperties({});
      setInitialFormState({
        formData: newFormData,
        properties: "{}",
        formProperties: {},
      });
    }
  }, [editingTransaction]);

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFormPropertyChange = (key: string, value: string) => {
    setFormProperties((prev) => ({ ...prev, [key]: value }));
  };

  const addFormProperty = () => {
    const newKey = `property_${Object.keys(formProperties).length + 1}`;
    setFormProperties((prev) => ({ ...prev, [newKey]: "" }));
  };

  const removeFormProperty = (key: string) => {
    setFormProperties((prev) => {
      const newProps = { ...prev };
      delete newProps[key];
      return newProps;
    });
  };

  const handleModeChange = (mode: "form" | "json") => {
    setPropertiesMode(mode);
    // Sync between form and JSON modes
    if (mode === "json") {
      // Convert form properties to JSON
      const jsonProps = Object.fromEntries(
        Object.entries(formProperties).map(([key, value]) => [
          key.replace(/^property_\d+$/, key.replace(/^property_/, "prop_")),
          value,
        ])
      );
      setProperties(JSON.stringify(jsonProps, null, 2));
    } else {
      // Convert JSON to form properties
      try {
        const jsonProps = JSON.parse(properties);
        const formProps: { [key: string]: string } = {};
        Object.entries(jsonProps).forEach(([key, value], index) => {
          formProps[`property_${index + 1}`] =
            typeof value === "string" ? value : JSON.stringify(value);
        });
        setFormProperties(formProps);
      } catch (error) {
        console.error("Error converting JSON to form properties:", error);
      }
    }
  };

  const formatJson = (jsonString: string): string => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return jsonString;
    }
  };

  const isJsonFormatted = (jsonString: string): boolean => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2) === jsonString;
    } catch {
      return false;
    }
  };

  const createMutation = useMutation({
    mutationFn: (data: CreateTransactionRequest) =>
      apiService.createTransaction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setShowSuccessSnackbar(true);
      onSuccess?.();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateTransactionRequest) =>
      apiService.updateTransaction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setShowSuccessSnackbar(true);
      onSuccess?.();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!dbUserId) {
      alert("User ID not available");
      return;
    }

    // Prepare properties based on mode
    let finalProperties: any = undefined;
    if (propertiesMode === "form") {
      // Convert form properties to object, filtering out empty values
      const nonEmptyProps = Object.fromEntries(
        Object.entries(formProperties).filter(
          ([key, value]) => value.trim() !== ""
        )
      );
      if (Object.keys(nonEmptyProps).length > 0) {
        finalProperties = nonEmptyProps;
      }
    } else {
      // Use JSON properties
      if (properties !== "{}") {
        finalProperties = JSON.parse(properties);
      }
    }

    const submitData = {
      user_id: dbUserId,
      portfolio_entity_id: parseInt(formData.portfolio_entity_id),
      contra_entity_id: parseInt(formData.contra_entity_id),
      instrument_entity_id: parseInt(formData.instrument_entity_id),
      transaction_type_id: parseInt(formData.transaction_type_id),
      transaction_status_id: parseInt(formData.transaction_status_id),
      properties: finalProperties,
    };

    if (editingTransaction) {
      updateMutation.mutate({
        ...submitData,
        transaction_id: editingTransaction.transaction_id,
      });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleCancel = () => {
    setFormData(initialFormState.formData);
    setProperties(initialFormState.properties);
    setFormProperties(initialFormState.formProperties);
    onClose?.();
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  return (
    <Paper sx={{ p: 3, maxHeight: "90vh", overflow: "auto" }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "An error occurred"}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit}>
        {/* Header with Transaction Type */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Typography variant="h5">
            {editingTransaction ? "Edit Transaction" : "Create Transaction"}
          </Typography>
          <Box sx={{ minWidth: 300 }}>
            <Autocomplete
              options={transactionTypes || []}
              getOptionLabel={(option) => option.name}
              value={
                transactionTypes?.find(
                  (t) =>
                    t.transaction_type_id.toString() ===
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
          </Box>
        </Box>

        {/* Line 2: Portfolio and contra */}
        <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
          <Autocomplete
            options={entities || []}
            getOptionLabel={(option) => option.name}
            value={
              entities?.find(
                (e) => e.entity_id.toString() === formData.portfolio_entity_id
              ) || null
            }
            onChange={(_, newValue) =>
              handleInputChange(
                "portfolio_entity_id",
                newValue?.entity_id.toString() || ""
              )
            }
            renderInput={(params) => (
              <TextField {...params} label="Portfolio *" required fullWidth />
            )}
            disabled={isLoading}
            sx={{ flex: 1 }}
          />
          <Autocomplete
            options={entities || []}
            getOptionLabel={(option) => option.name}
            value={
              entities?.find(
                (e) => e.entity_id.toString() === formData.contra_entity_id
              ) || null
            }
            onChange={(_, newValue) =>
              handleInputChange(
                "contra_entity_id",
                newValue?.entity_id.toString() || ""
              )
            }
            renderInput={(params) => (
              <TextField {...params} label="contra *" required fullWidth />
            )}
            disabled={isLoading}
            sx={{ flex: 1 }}
          />
        </Box>

        {/* Line 3: Instrument */}
        <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
          <Autocomplete
            options={entities || []}
            getOptionLabel={(option) => option.name}
            value={
              entities?.find(
                (e) => e.entity_id.toString() === formData.instrument_entity_id
              ) || null
            }
            onChange={(_, newValue) =>
              handleInputChange(
                "instrument_entity_id",
                newValue?.entity_id.toString() || ""
              )
            }
            renderInput={(params) => (
              <TextField {...params} label="Instrument *" required fullWidth />
            )}
            disabled={isLoading}
            sx={{ flex: 1 }}
          />
        </Box>

        {/* Line 4: Transaction Type and Status */}
        <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
          <Autocomplete
            options={transactionTypes || []}
            getOptionLabel={(option) => option.name}
            value={
              transactionTypes?.find(
                (t) =>
                  t.transaction_type_id.toString() ===
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
            sx={{ flex: 1 }}
          />
          <Autocomplete
            options={transactionStatuses || []}
            getOptionLabel={(option) => option.name}
            value={
              transactionStatuses?.find(
                (s) =>
                  s.transaction_status_id.toString() ===
                  formData.transaction_status_id
              ) || null
            }
            onChange={(_, newValue) =>
              handleInputChange(
                "transaction_status_id",
                newValue?.transaction_status_id.toString() || ""
              )
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Transaction Status *"
                required
                fullWidth
              />
            )}
            disabled={isLoading}
            sx={{ flex: 1 }}
          />
        </Box>

        {/* Transaction Properties */}
        <Box sx={{ mt: 2 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">Transaction Properties</Typography>
            <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
              <FormJsonToggle
                mode={propertiesMode}
                onModeChange={handleModeChange}
              />
              {propertiesMode === "form" && (
                <Button
                  variant="outlined"
                  onClick={addFormProperty}
                  disabled={isLoading}
                  size="small"
                >
                  Add Property
                </Button>
              )}
            </Box>
          </Box>

          {propertiesMode === "form" ? (
            <Box sx={{ mt: 2 }}>
              {Object.keys(formProperties).length === 0 ? (
                <Box
                  sx={{
                    p: 3,
                    border: "1px solid #e0e0e0",
                    borderRadius: 2,
                    backgroundColor: "#fafafa",
                    textAlign: "center",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No custom properties added yet. Click "Add Property" to add
                    key-value pairs.
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {Object.entries(formProperties).map(([key, value]) => (
                    <Box
                      key={key}
                      sx={{ display: "flex", gap: 2, alignItems: "center" }}
                    >
                      <TextField
                        label="Property Key"
                        value={key}
                        onChange={(e) => {
                          const newKey = e.target.value;
                          const newProps = { ...formProperties };
                          delete newProps[key];
                          newProps[newKey] = value;
                          setFormProperties(newProps);
                        }}
                        size="small"
                        sx={{ flex: 1 }}
                        disabled={isLoading}
                      />
                      <TextField
                        label="Property Value"
                        value={value}
                        onChange={(e) =>
                          handleFormPropertyChange(key, e.target.value)
                        }
                        size="small"
                        sx={{ flex: 1 }}
                        disabled={isLoading}
                      />
                      <Button
                        variant="outlined"
                        color="error"
                        onClick={() => removeFormProperty(key)}
                        disabled={isLoading}
                        size="small"
                        sx={{ minWidth: "auto", px: 1 }}
                      >
                        ×
                      </Button>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          ) : (
            <Box sx={{ mt: 2 }}>
              <AceEditor
                mode="json"
                theme="github"
                value={properties}
                onChange={(value) => {
                  setProperties(value);
                  setJsonError("");
                }}
                onValidate={(annotations) => {
                  const hasError = annotations.some(
                    (annotation) => annotation.type === "error"
                  );
                  setJsonError(hasError ? "Invalid JSON format" : "");
                }}
                name="properties-editor"
                editorProps={{ $blockScrolling: true }}
                width="100%"
                height="200px"
                fontSize={14}
                showPrintMargin={false}
                showGutter={true}
                highlightActiveLine={true}
                setOptions={{
                  enableBasicAutocompletion: true,
                  enableLiveAutocompletion: true,
                  enableSnippets: true,
                  showLineNumbers: true,
                  tabSize: 2,
                }}
              />
              {jsonError && (
                <Typography
                  color="error"
                  variant="caption"
                  sx={{ mt: 1, display: "block" }}
                >
                  {jsonError}
                </Typography>
              )}
            </Box>
          )}
        </Box>
        {/* Audit Trail */}
        {editingTransaction && (
          <AuditTrail
            updateDate={editingTransaction.update_date}
            updatedUserId={editingTransaction.updated_user_id}
          />
        )}

        {/* Action Buttons */}
        <Box
          sx={{ display: "flex", gap: 2, mt: 4, justifyContent: "flex-end" }}
        >
          <Button
            type="submit"
            variant="contained"
            color="primary"
            onClick={handleSubmit}
            disabled={isLoading || !!jsonError}
            size="large"
            sx={{
              minWidth: 180,
              fontWeight: 600,
              textTransform: "none",
            }}
          >
            {isLoading
              ? "Saving..."
              : editingTransaction
              ? "Update Transaction"
              : "Create Transaction"}
          </Button>
          <Button
            variant="outlined"
            onClick={handleCancel}
            disabled={isLoading}
            size="large"
            sx={{
              minWidth: 120,
              fontWeight: 600,
              textTransform: "none",
            }}
          >
            Cancel
          </Button>
        </Box>
      </Box>

      <Snackbar
        open={showSuccessSnackbar}
        autoHideDuration={3000}
        onClose={() => setShowSuccessSnackbar(false)}
        message={
          editingTransaction
            ? "Transaction updated successfully!"
            : "Transaction created successfully!"
        }
      />
    </Paper>
  );
};

export default TransactionForm;
