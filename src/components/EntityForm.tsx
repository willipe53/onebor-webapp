import React, { useState, useMemo, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Autocomplete,
  Checkbox,
  FormControlLabel,
  Grid,
  Snackbar,
  Chip,
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import * as apiService from "../services/api";
import FormJsonToggle from "./FormJsonToggle";
import {
  prettyPrint,
  isValidEmail,
  formatDateForInput,
  prepareJsonForForm,
} from "../utils";
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-github";

interface FormField {
  key: string;
  type: string;
  format?: string;
  required?: boolean;
  value: any;
}

interface EntityFormProps {
  editingEntity?: any;
  onClose?: () => void;
}

const EntityForm: React.FC<EntityFormProps> = ({ editingEntity, onClose }) => {
  const { userId } = useAuth();
  const [name, setName] = useState("");
  const [selectedParentEntity, setSelectedParentEntity] =
    useState<apiService.Entity | null>(null);
  const [selectedEntityType, setSelectedEntityType] =
    useState<apiService.EntityType | null>(null);
  const [dynamicFields, setDynamicFields] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [attributesMode, setAttributesMode] = useState<"form" | "json">("form");
  const [jsonAttributes, setJsonAttributes] = useState<string>("");
  const [jsonError, setJsonError] = useState<string>("");
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [initialFormState, setInitialFormState] = useState<{
    name: string;
    selectedParentEntity: apiService.Entity | null;
    selectedEntityType: apiService.EntityType | null;
    dynamicFields: Record<string, any>;
    jsonAttributes: string;
  } | null>(null);

  const queryClient = useQueryClient();

  // Function to check if form is dirty
  const checkIfDirty = useCallback(() => {
    if (!initialFormState) return false;

    const currentState = {
      name,
      selectedParentEntity,
      selectedEntityType,
      dynamicFields,
      jsonAttributes,
    };

    return (
      currentState.name !== initialFormState.name ||
      currentState.selectedParentEntity?.entity_id !==
        initialFormState.selectedParentEntity?.entity_id ||
      currentState.selectedEntityType?.entity_type_id !==
        initialFormState.selectedEntityType?.entity_type_id ||
      JSON.stringify(currentState.dynamicFields) !==
        JSON.stringify(initialFormState.dynamicFields) ||
      currentState.jsonAttributes !== initialFormState.jsonAttributes
    );
  }, [
    name,
    selectedParentEntity,
    selectedEntityType,
    dynamicFields,
    jsonAttributes,
    initialFormState,
  ]);

  // Update dirty state whenever form values change
  useEffect(() => {
    setIsDirty(checkIfDirty());
  }, [checkIfDirty]);

  // Fetch user data to get primary client group
  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["users", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
  });

  const currentUser = users && users.length > 0 ? users[0] : null;

  // Debug logging
  console.log("🔍 EntityForm - userId:", userId);
  console.log("🔍 EntityForm - users:", users);
  console.log("🔍 EntityForm - currentUser:", currentUser);
  console.log("🔍 EntityForm - usersLoading:", usersLoading);

  // Fetch entity types for the dropdown
  const { data: rawEntityTypesData, isLoading: entityTypesLoading } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => apiService.queryEntityTypes({}),
  });

  // Fetch entities for parent dropdown
  const { data: rawEntitiesData, isLoading: entitiesLoading } = useQuery({
    queryKey: ["entities", currentUser?.user_id],
    queryFn: () => apiService.queryEntities({ user_id: currentUser!.user_id }),
    enabled: !!currentUser?.user_id,
  });

  // Use entity types data directly since it's an array
  const entityTypesData = rawEntityTypesData || [];

  // Transform entities data for parent dropdown
  const entitiesData = useMemo(() => {
    if (!rawEntitiesData) return [];

    // Check if data is already in object format
    if (
      Array.isArray(rawEntitiesData) &&
      rawEntitiesData.length > 0 &&
      typeof rawEntitiesData[0] === "object" &&
      "entity_id" in rawEntitiesData[0]
    ) {
      return rawEntitiesData;
    }

    // Transform array format [id, name, type_id, parent_id, attributes] to object format
    if (Array.isArray(rawEntitiesData)) {
      return rawEntitiesData.map((row: any) => {
        if (Array.isArray(row) && row.length >= 5) {
          return {
            entity_id: row[0],
            name: row[1],
            entity_type_id: row[2],
            parent_entity_id: row[3],
            attributes:
              typeof row[4] === "string" ? JSON.parse(row[4]) : row[4],
          };
        }
        return row;
      });
    }

    return rawEntitiesData;
  }, [rawEntitiesData]);

  // Extract schema fields from selected entity type
  const schemaFields = useMemo<FormField[]>(() => {
    const fields: FormField[] = [];
    const addedKeys = new Set<string>();

    // First, add all fields from the schema
    if (selectedEntityType?.attributes_schema?.properties) {
      const properties = selectedEntityType.attributes_schema.properties;
      const required = selectedEntityType.attributes_schema.required || [];

      Object.entries(properties).forEach(([key, schema]: [string, any]) => {
        fields.push({
          key,
          type: schema.type || "string",
          format: schema.format,
          required: required.includes(key),
          value: dynamicFields[key] || "",
        });
        addedKeys.add(key);
      });
    }

    // Then, add any additional fields from actual entity attributes (for editing)
    if (editingEntity?.attributes) {
      let parsedAttributes;

      if (typeof editingEntity.attributes === "string") {
        try {
          parsedAttributes = JSON.parse(editingEntity.attributes);
        } catch {
          parsedAttributes = {};
        }
      } else if (typeof editingEntity.attributes === "object") {
        parsedAttributes = editingEntity.attributes;
      } else {
        parsedAttributes = {};
      }

      Object.keys(parsedAttributes).forEach((key) => {
        if (!addedKeys.has(key)) {
          // This field exists in the entity but not in the schema
          const value = dynamicFields[key] || parsedAttributes[key] || "";
          const valueType = typeof parsedAttributes[key];

          // Detect type from existing value
          let fieldType = "string"; // Default
          if (valueType === "boolean") {
            fieldType = "boolean";
          } else if (valueType === "number") {
            fieldType = Number.isInteger(parsedAttributes[key])
              ? "integer"
              : "number";
          } else if (valueType === "object" && parsedAttributes[key] !== null) {
            fieldType = Array.isArray(parsedAttributes[key])
              ? "array"
              : "object";
          }

          fields.push({
            key,
            type: fieldType,
            format: undefined,
            required: false, // Non-schema fields are not required
            value,
          });
          addedKeys.add(key);
        }
      });
    }

    // Finally, add any additional fields from dynamicFields (from JSON editing)
    Object.keys(dynamicFields).forEach((key) => {
      if (!addedKeys.has(key)) {
        // This field was added via JSON editing but doesn't exist in schema or original entity
        const value = dynamicFields[key] || "";
        const valueType = typeof dynamicFields[key];

        // Detect type from current value
        let fieldType = "string"; // Default
        if (valueType === "boolean") {
          fieldType = "boolean";
        } else if (valueType === "number") {
          fieldType = Number.isInteger(dynamicFields[key])
            ? "integer"
            : "number";
        } else if (valueType === "object" && dynamicFields[key] !== null) {
          fieldType = Array.isArray(dynamicFields[key]) ? "array" : "object";
        }

        fields.push({
          key,
          type: fieldType,
          format: undefined,
          required: false,
          value,
        });
        addedKeys.add(key);
      }
    });

    return fields;
  }, [selectedEntityType, dynamicFields, editingEntity]);

  // Populate form when editing an entity
  useEffect(() => {
    if (editingEntity) {
      setName(editingEntity.name || "");

      // Find and set the parent entity
      if (editingEntity.parent_entity_id && entitiesData) {
        const parent = entitiesData.find(
          (e) => e.entity_id === editingEntity.parent_entity_id
        );
        setSelectedParentEntity(parent || null);
      }

      // Find and set the entity type
      if (editingEntity.entity_type_id && entityTypesData) {
        const entityType = entityTypesData.find(
          (et) => et.entity_type_id === editingEntity.entity_type_id
        );
        setSelectedEntityType(entityType || null);
      }

      // Set dynamic fields from attributes using utility
      if (editingEntity.attributes) {
        const { object: parsedAttributes, jsonString } = prepareJsonForForm(
          editingEntity.attributes
        );
        setDynamicFields(parsedAttributes);
        setJsonAttributes(jsonString);
      }

      // Set initial form state for dirty tracking (after all fields are populated)
      setTimeout(() => {
        setInitialFormState({
          name: editingEntity.name || "",
          selectedParentEntity:
            editingEntity.parent_entity_id && entitiesData
              ? entitiesData.find(
                  (e) => e.entity_id === editingEntity.parent_entity_id
                ) || null
              : null,
          selectedEntityType:
            editingEntity.entity_type_id && entityTypesData
              ? entityTypesData.find(
                  (et) => et.entity_type_id === editingEntity.entity_type_id
                ) || null
              : null,
          dynamicFields: editingEntity.attributes
            ? prepareJsonForForm(editingEntity.attributes).object
            : {},
          jsonAttributes: editingEntity.attributes
            ? prepareJsonForForm(editingEntity.attributes).jsonString
            : "",
        });
        setIsDirty(false); // Reset dirty state when loading existing entity
      }, 0);
    } else {
      // For new entities, set initial state immediately
      setInitialFormState({
        name: "",
        selectedParentEntity: null,
        selectedEntityType: null,
        dynamicFields: {},
        jsonAttributes: "",
      });
      setIsDirty(false);
    }
  }, [editingEntity, entitiesData, entityTypesData]);

  // Handle switching between form and JSON modes
  const handleModeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: "form" | "json"
  ) => {
    if (newMode === null) return; // Don't allow deselecting

    if (newMode === "json" && attributesMode === "form") {
      // Switching from form to JSON - convert dynamicFields to JSON string
      setJsonAttributes(JSON.stringify(dynamicFields, null, 2));
      setJsonError("");
    } else if (newMode === "form" && attributesMode === "json") {
      // Switching from JSON to form - validate and parse JSON
      try {
        const parsed = JSON.parse(jsonAttributes);
        setDynamicFields(parsed);
        setJsonError("");
      } catch {
        setJsonError("Invalid JSON syntax");
        return; // Don't switch modes if JSON is invalid
      }
    }

    setAttributesMode(newMode);
  };

  // Handle JSON editor changes
  const handleJsonChange = (value: string) => {
    setJsonAttributes(value);

    // Validate JSON syntax
    try {
      if (value.trim()) {
        JSON.parse(value);
      }
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON syntax");
    }
  };

  // Format JSON string
  const formatJson = () => {
    try {
      const parsed = JSON.parse(jsonAttributes);
      const formatted = JSON.stringify(parsed, null, 2);
      setJsonAttributes(formatted);
      setJsonError("");
    } catch {
      setJsonError("Cannot format invalid JSON");
    }
  };

  // Check if JSON is already formatted
  const isJsonFormatted = () => {
    try {
      const parsed = JSON.parse(jsonAttributes);
      const formatted = JSON.stringify(parsed, null, 2);
      return jsonAttributes === formatted;
    } catch {
      return false;
    }
  };

  const mutation = useMutation({
    mutationFn: (data: apiService.UpdateEntityRequest) => {
      if (editingEntity?.entity_id) {
        return apiService.updateEntity(data);
      } else {
        return apiService.createEntity(data as apiService.CreateEntityRequest);
      }
    },
    onSuccess: () => {
      if (!editingEntity?.entity_id) {
        // Reset form only for create mode
        setName("");
        setSelectedParentEntity(null);
        setSelectedEntityType(null);
        setDynamicFields({});
        setErrors({});
        setAttributesMode("form");
        setJsonAttributes("{}");
        setJsonError("");
      }
      // Show success notification
      setShowSuccessSnackbar(true);

      // Invalidate and refetch entities queries to refresh tables immediately
      queryClient.invalidateQueries({ queryKey: ["entities"] });
      queryClient.refetchQueries({ queryKey: ["entities"] });

      // Close modal after success (with a small delay to show the success message)
      if (onClose) {
        setTimeout(() => {
          onClose();
        }, 1000); // 1 second delay to show success message
      }
    },
    onError: (error: any) => {
      console.error(
        `Entity ${editingEntity?.entity_id ? "update" : "creation"} failed:`,
        error
      );

      // Show user-friendly error message
      if (
        error.message &&
        error.message.includes("404") &&
        error.message.includes("not found")
      ) {
        alert(
          "Error: This entity no longer exists in the database. Please refresh the page and try again."
        );
        // Optionally refresh the entities data
        queryClient.invalidateQueries({ queryKey: ["entities"] });
        if (onClose) {
          onClose();
        }
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Don't submit if user data is still loading
    if (usersLoading) {
      console.log("⏳ User data still loading, preventing submission");
      return;
    }

    // Validate required fields
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = "Name is required";
    if (!selectedEntityType) newErrors.entityType = "Entity type is required";

    // Validate dynamic fields
    schemaFields.forEach((field) => {
      if (field.required && !field.value) {
        newErrors[field.key] = `${prettyPrint(field.key)} is required`;
      }
      if (
        field.format === "email" &&
        field.value &&
        !isValidEmail(field.value)
      ) {
        newErrors[field.key] = "Invalid email format";
      }
    });

    setErrors(newErrors);

    // Validate JSON mode if applicable
    let finalAttributes = dynamicFields;
    if (attributesMode === "json") {
      if (jsonError) {
        newErrors.json = "Please fix JSON syntax errors before submitting";
      } else {
        try {
          finalAttributes = JSON.parse(jsonAttributes);
        } catch {
          newErrors.json = "Invalid JSON syntax";
        }
      }
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) return;

    // Prepare request data
    const requestData: apiService.UpdateEntityRequest = {
      user_id: currentUser!.user_id,
      name,
      entity_type_id: selectedEntityType?.entity_type_id,
      parent_entity_id: selectedParentEntity?.entity_id || null,
      attributes: finalAttributes,
    };

    // Add entity_id for updates
    if (editingEntity?.entity_id) {
      requestData.entity_id = editingEntity.entity_id;
    } else {
      // For new entities, add client_group_id
      console.log("🔍 Creating new entity - currentUser:", currentUser);
      console.log(
        "🔍 primary_client_group_id:",
        currentUser?.primary_client_group_id
      );

      if (!currentUser?.primary_client_group_id) {
        console.log("❌ No primary_client_group_id found");
        setErrors({
          general:
            "No client group assigned. Please contact your administrator.",
        });
        return;
      }
      requestData.client_group_id = currentUser.primary_client_group_id;
      console.log("✅ Added client_group_id:", requestData.client_group_id);
    }

    mutation.mutate(requestData);
  };

  const handleEntityTypeChange = (entityType: apiService.EntityType | null) => {
    setSelectedEntityType(entityType);
    setDynamicFields({}); // Reset dynamic fields when entity type changes
    setErrors({});
    setJsonAttributes("{}");
    setJsonError("");
  };

  const handleDynamicFieldChange = (key: string, value: any) => {
    setDynamicFields((prev) => ({
      ...prev,
      [key]: value,
    }));

    // Clear error for this field
    if (errors[key]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  const renderSchemaField = (field: FormField) => {
    const prettyLabel = prettyPrint(field.key);
    const value = dynamicFields[field.key] || "";
    const error = errors[field.key];
    const isRequired = field.required;

    // Check if this field is from the schema or from actual entity data
    const isSchemaField =
      selectedEntityType?.attributes_schema?.properties?.[field.key];
    const label = isSchemaField
      ? `${prettyLabel}${isRequired ? " *" : ""}`
      : `${prettyLabel} (Custom)`; // Mark non-schema fields

    // Date field
    if (field.type === "string" && field.format === "date") {
      return (
        <Grid key={field.key}>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker
              label={label}
              value={value ? new Date(value) : null}
              onChange={(newValue) => {
                const dateStr = newValue ? formatDateForInput(newValue) : "";
                handleDynamicFieldChange(field.key, dateStr);
              }}
              slotProps={{
                textField: {
                  fullWidth: true,
                  error: !!error,
                  helperText: error,
                },
              }}
            />
          </LocalizationProvider>
        </Grid>
      );
    }

    // Email field
    if (field.format === "email") {
      return (
        <Grid key={field.key}>
          <TextField
            fullWidth
            label={label}
            type="email"
            value={value}
            onChange={(e) =>
              handleDynamicFieldChange(field.key, e.target.value)
            }
            error={!!error}
            helperText={error}
            placeholder="example@domain.com"
          />
        </Grid>
      );
    }

    // Number field
    if (field.type === "number" || field.type === "integer") {
      return (
        <Grid key={field.key}>
          <TextField
            fullWidth
            label={label}
            type="number"
            value={value}
            onChange={(e) =>
              handleDynamicFieldChange(
                field.key,
                e.target.value ? Number(e.target.value) : ""
              )
            }
            error={!!error}
            helperText={error}
          />
        </Grid>
      );
    }

    // Boolean field
    if (field.type === "boolean") {
      return (
        <Grid key={field.key}>
          <FormControlLabel
            control={
              <Checkbox
                checked={Boolean(value)}
                onChange={(e) =>
                  handleDynamicFieldChange(field.key, e.target.checked)
                }
                disabled={mutation.isPending}
              />
            }
            label={label}
          />
          {error && (
            <Typography variant="caption" color="error" display="block">
              {error}
            </Typography>
          )}
        </Grid>
      );
    }

    // Default text field
    return (
      <Grid key={field.key}>
        <TextField
          fullWidth
          label={label}
          value={value}
          onChange={(e) => handleDynamicFieldChange(field.key, e.target.value)}
          error={!!error}
          helperText={error}
          multiline={field.type === "object" || field.type === "array"}
          rows={field.type === "object" || field.type === "array" ? 3 : 1}
        />
      </Grid>
    );
  };

  if (entityTypesLoading || entitiesLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 3, maxWidth: 800, mx: "auto" }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h6">
          {editingEntity?.entity_id ? "Edit Entity" : "Create Entity"}
        </Typography>
        {editingEntity?.entity_id && (
          <Chip
            label={`ID: ${editingEntity.entity_id}`}
            size="small"
            variant="outlined"
            sx={{
              backgroundColor: "rgba(25, 118, 210, 0.1)",
              borderColor: "rgba(25, 118, 210, 0.5)",
              color: "primary.main",
              fontWeight: "500",
            }}
          />
        )}
      </Box>

      {mutation.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to {editingEntity?.entity_id ? "update" : "create"} entity:{" "}
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Unknown error"}
        </Alert>
      )}

      {errors.general && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors.general}
        </Alert>
      )}

      {mutation.isSuccess && !editingEntity?.entity_id && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Entity created successfully!
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit}>
        {/* First Line: Entity Name */}
        <TextField
          fullWidth
          label="Entity Name *"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={!!errors.name}
          helperText={errors.name}
          disabled={mutation.isPending}
          sx={{ mb: 3 }}
        />

        {/* Second Line: Parent Entity */}
        <Autocomplete
          options={(entitiesData || []).filter(
            (entity) =>
              // Exclude the current entity from parent options when editing
              // (an entity cannot be its own parent)
              !editingEntity || entity.entity_id !== editingEntity.entity_id
          )}
          getOptionLabel={(option) => {
            if (!option.name) return "";

            // Find the entity type name for this entity
            const entityType = entityTypesData?.find(
              (type) => type.entity_type_id === option.entity_type_id
            );
            const typeName = entityType?.name || "Unknown Type";

            return `${option.name} (${typeName})`;
          }}
          getOptionKey={(option) => option.entity_id}
          value={selectedParentEntity}
          onChange={(_, newValue) => setSelectedParentEntity(newValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Parent Entity"
              helperText="Optional: Select a parent entity"
              disabled={mutation.isPending}
            />
          )}
          disabled={mutation.isPending}
          sx={{ mb: 3 }}
        />

        {/* Third Line: Entity Type */}
        <Autocomplete
          options={entityTypesData || []}
          getOptionLabel={(option) => option.name || ""}
          getOptionKey={(option) => option.entity_type_id}
          value={selectedEntityType}
          onChange={(_, newValue) => handleEntityTypeChange(newValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Entity Type *"
              error={!!errors.entityType}
              helperText={errors.entityType}
              disabled={mutation.isPending}
            />
          )}
          disabled={mutation.isPending}
          sx={{ mb: 3 }}
        />

        {/* Dynamic Schema Fields Box */}
        {selectedEntityType && schemaFields.length > 0 && (
          <Paper
            variant="outlined"
            sx={{ p: 3, mb: 3, backgroundColor: "rgba(0, 0, 0, 0.02)" }}
          >
            {/* Header with title and mode toggle */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 3,
              }}
            >
              <Typography
                variant="h6"
                sx={{ fontWeight: "medium", color: "primary.main" }}
              >
                {selectedEntityType.name} Properties
              </Typography>

              <FormJsonToggle
                value={attributesMode}
                onChange={handleModeChange}
                disabled={mutation.isPending}
              />
            </Box>

            {/* Form fields mode */}
            {attributesMode === "form" && (
              <Grid container spacing={3}>
                {schemaFields.map(renderSchemaField)}
              </Grid>
            )}

            {/* JSON mode */}
            {attributesMode === "json" && (
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 2,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Edit attributes as JSON (Advanced)
                  </Typography>
                  <Button
                    size="small"
                    onClick={formatJson}
                    disabled={
                      !jsonAttributes.trim() || isJsonFormatted() || !!jsonError
                    }
                    sx={{ textTransform: "none" }}
                  >
                    Format JSON
                  </Button>
                </Box>

                {jsonError && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {jsonError}
                  </Alert>
                )}

                <Box
                  sx={{
                    border: jsonError ? "2px solid #f44336" : "1px solid #ccc",
                    borderRadius: 1,
                    overflow: "hidden",
                  }}
                >
                  <AceEditor
                    mode="json"
                    theme="github"
                    value={jsonAttributes}
                    onChange={handleJsonChange}
                    name="json-attributes-editor"
                    width="100%"
                    height="300px"
                    fontSize={14}
                    showPrintMargin={false}
                    showGutter={true}
                    highlightActiveLine={true}
                    setOptions={{
                      enableBasicAutocompletion: false,
                      enableLiveAutocompletion: false,
                      enableSnippets: false,
                      showLineNumbers: true,
                      tabSize: 2,
                      useWorker: false,
                    }}
                  />
                </Box>

                {errors.json && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {errors.json}
                  </Alert>
                )}
              </Box>
            )}
          </Paper>
        )}

        {/* Action Buttons */}
        <Box
          sx={{ display: "flex", justifyContent: "flex-end", gap: 2, mt: 3 }}
        >
          {editingEntity && onClose && (
            <Button
              variant="outlined"
              size="large"
              onClick={onClose}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={
              mutation.isPending ||
              !name.trim() ||
              !selectedEntityType ||
              (editingEntity?.entity_id && !isDirty) // Disable if editing existing entity and not dirty
            }
          >
            {mutation.isPending ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                {editingEntity ? "Updating..." : "Creating..."}
              </>
            ) : editingEntity?.entity_id ? (
              `Update ${editingEntity.name}`
            ) : (
              "Create Entity"
            )}
          </Button>
        </Box>
      </Box>

      {/* Success notification */}
      <Snackbar
        open={showSuccessSnackbar}
        autoHideDuration={3000}
        onClose={() => setShowSuccessSnackbar(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity="success"
          onClose={() => setShowSuccessSnackbar(false)}
          sx={{ width: "100%" }}
        >
          {editingEntity
            ? "Entity updated successfully!"
            : "Entity created successfully!"}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default EntityForm;
