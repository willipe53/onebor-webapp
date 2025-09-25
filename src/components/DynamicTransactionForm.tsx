import React, { useState, useEffect, useMemo } from "react";
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
  Divider,
  Stack,
} from "@mui/material";
import { Add } from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import * as apiService from "../services/api";
import EntityForm from "./EntityForm";

interface DynamicTransactionFormProps {
  editingTransaction?: apiService.Transaction;
  onClose?: () => void;
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
  counterparty_entity_id: string;
  properties: Record<string, any>;
}

const DynamicTransactionForm: React.FC<DynamicTransactionFormProps> = ({
  editingTransaction,
  onClose,
}) => {
  const { userId, dbUserId } = useAuth();
  const queryClient = useQueryClient();

  // Form state
  const [formData, setFormData] = useState<FormData>({
    portfolio_entity_id: "",
    instrument_entity_id: "",
    transaction_type_id: "",
    counterparty_entity_id: "",
    properties: {},
  });

  // Step tracking
  const [currentStep, setCurrentStep] = useState(0);
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);

  // Entity creation modals
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [showInstrumentModal, setShowInstrumentModal] = useState(false);
  const [showCounterpartyModal, setShowCounterpartyModal] = useState(false);

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

  // Get transaction statuses
  const { data: transactionStatuses } = useQuery({
    queryKey: ["transaction-statuses"],
    queryFn: () => apiService.queryTransactionStatuses({}),
  });

  // Filter entities by type
  const portfolioEntities = useMemo(() => {
    if (!entities || !entityTypes) return [];

    const portfolioType = entityTypes.find((et) => et.name === "Portfolio");
    if (!portfolioType) return [];

    return entities.filter(
      (entity) => entity.entity_type_id === portfolioType.entity_type_id
    );
  }, [entities, entityTypes]);

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
    mutationFn: (data: apiService.CreateTransactionRequest) =>
      editingTransaction
        ? apiService.updateTransaction({
            ...data,
            transaction_id: editingTransaction.transaction_id,
          })
        : apiService.createTransaction(data),
    onSuccess: () => {
      setShowSuccessSnackbar(true);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.refetchQueries({ queryKey: ["transactions"] });
      if (onClose) {
        setTimeout(() => onClose(), 1000);
      }
    },
  });

  // Handle form submission
  const handleSubmit = () => {
    if (!dbUserId) return;

    const submitData: apiService.CreateTransactionRequest = {
      user_id: dbUserId,
      portfolio_entity_id: parseInt(formData.portfolio_entity_id),
      instrument_entity_id: parseInt(formData.instrument_entity_id),
      transaction_type_id: parseInt(formData.transaction_type_id),
      counterparty_entity_id: parseInt(formData.counterparty_entity_id),
      properties: formData.properties,
    };

    mutation.mutate(submitData);
  };

  // Handle input changes
  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    // Reset subsequent steps when earlier selections change
    if (field === "portfolio_entity_id") {
      setFormData((prev) => ({
        ...prev,
        instrument_entity_id: "",
        transaction_type_id: "",
        counterparty_entity_id: "",
        properties: {},
      }));
      setCurrentStep(1);
    } else if (field === "instrument_entity_id") {
      setFormData((prev) => ({
        ...prev,
        transaction_type_id: "",
        counterparty_entity_id: "",
        properties: {},
      }));
      setCurrentStep(2);
    } else if (field === "transaction_type_id") {
      setFormData((prev) => ({
        ...prev,
        counterparty_entity_id: "",
        properties: {},
      }));
      setCurrentStep(3);
    } else if (field === "counterparty_entity_id") {
      setCurrentStep(4);
    }
  };

  // Handle property changes
  const handlePropertyChange = (propertyName: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      properties: {
        ...prev.properties,
        [propertyName]: value,
      },
    }));
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

  const handleCounterpartyCreated = (newEntity: any) => {
    setFormData((prev) => ({
      ...prev,
      counterparty_entity_id: newEntity.entity_id.toString(),
    }));
    setShowCounterpartyModal(false);
    setCurrentStep(4);
    // Refresh entities data
    queryClient.invalidateQueries({ queryKey: ["entities"] });
  };

  // Check if form can be submitted
  const canSubmit = useMemo(() => {
    return (
      formData.portfolio_entity_id &&
      formData.instrument_entity_id &&
      formData.transaction_type_id &&
      formData.counterparty_entity_id &&
      transactionSchema &&
      transactionSchema.required?.every(
        (req) => formData.properties[req] !== undefined
      )
    );
  }, [formData, transactionSchema]);

  // Render property field based on schema
  const renderPropertyField = (propertyName: string, propertySchema: any) => {
    const value = formData.properties[propertyName] || "";
    const isRequired = transactionSchema?.required?.includes(propertyName);

    if (propertySchema.type === "string" && propertySchema.format === "date") {
      return (
        <DatePicker
          key={propertyName}
          label={`${propertyName}${isRequired ? " *" : ""}`}
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
              label={`${propertyName}${isRequired ? " *" : ""}`}
              required={isRequired}
              fullWidth
            />
          )}
        />
      );
    }

    return (
      <TextField
        key={propertyName}
        label={`${propertyName}${isRequired ? " *" : ""}`}
        value={value}
        onChange={(e) => handlePropertyChange(propertyName, e.target.value)}
        required={isRequired}
        fullWidth
        type={propertySchema.type === "number" ? "number" : "text"}
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
          <Step>
            <StepLabel>Counterparty</StepLabel>
          </Step>
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

        {/* Step 4: Counterparty Selection */}
        {formData.transaction_type_id && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                4. Select Counterparty
              </Typography>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Autocomplete
                  options={validCounterparties || []}
                  getOptionLabel={(option) => option.name}
                  value={
                    validCounterparties?.find(
                      (e) =>
                        e.entity_id.toString() ===
                        formData.counterparty_entity_id
                    ) || null
                  }
                  onChange={(_, newValue) =>
                    handleInputChange(
                      "counterparty_entity_id",
                      newValue?.entity_id.toString() || ""
                    )
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Counterparty *"
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
                  onClick={() => setShowCounterpartyModal(true)}
                  disabled={isLoading}
                  sx={{ minWidth: "auto", px: 2 }}
                >
                  Add New
                </Button>
              </Stack>
              {validCounterparties.length === 0 && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  No valid counterparties found for the selected instrument and
                  transaction type.
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 5: Dynamic Properties */}
        {formData.counterparty_entity_id && transactionSchema && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                5. Transaction Properties
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
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
              onClick={onClose}
              disabled={mutation.isPending}
            >
              Cancel
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

        {/* Counterparty Creation Modal */}
        {showCounterpartyModal && (
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
                Create New Counterparty
              </Typography>
              <Box sx={{ maxHeight: "70vh", overflow: "auto" }}>
                <EntityForm
                  onClose={() => setShowCounterpartyModal(false)}
                  onSuccess={handleCounterpartyCreated}
                  allowedEntityTypes={validCounterparties
                    .map((cp) => {
                      const entityType = entityTypes?.find(
                        (et) => et.entity_type_id === cp.entity_type_id
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
      </Box>
    </LocalizationProvider>
  );
};

export default DynamicTransactionForm;
