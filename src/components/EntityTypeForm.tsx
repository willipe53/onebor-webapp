import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  FormControl,
  FormLabel,
  Snackbar,
  Chip,
} from "@mui/material";
import AceEditor from "react-ace";

// Import JSON mode and theme for ace editor
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-github";
import "ace-builds/src-noconflict/ext-language_tools";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as apiService from "../services/api";

interface EntityType {
  entity_type_id: number;
  name: string;
  attributes_schema: object | string;
  short_label?: string;
  label_color?: string;
}

interface EntityTypeFormProps {
  editingEntityType?: EntityType;
  onClose?: () => void;
}

// Predefined color palette similar to the image
const COLOR_PALETTE = [
  "#f44336", // Red
  "#e91e63", // Pink
  "#9c27b0", // Purple
  "#673ab7", // Deep Purple
  "#3f51b5", // Indigo
  "#2196f3", // Blue
  "#03a9f4", // Light Blue
  "#00bcd4", // Cyan
  "#009688", // Teal
  "#4caf50", // Green
  "#8bc34a", // Light Green
  "#cddc39", // Lime
  "#ffeb3b", // Yellow
  "#ffc107", // Amber
  "#ff9800", // Orange
  "#ff5722", // Deep Orange
];

const EntityTypeForm: React.FC<EntityTypeFormProps> = ({
  editingEntityType,
  onClose,
}) => {
  const [name, setName] = useState("");
  const [shortLabel, setShortLabel] = useState("");
  const [labelColor, setLabelColor] = useState("#4caf50"); // Default green
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [attributesSchema, setAttributesSchema] = useState(
    JSON.stringify(
      {
        type: "object",
        properties: {},
        required: [],
      },
      null,
      2
    )
  );
  const [jsonError, setJsonError] = useState("");
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);

  const queryClient = useQueryClient();

  // Populate form when editing an entity type
  useEffect(() => {
    if (editingEntityType) {
      setName(editingEntityType.name || "");
      setShortLabel(editingEntityType.short_label || "");

      // Handle label_color - add # prefix if missing
      let color = editingEntityType.label_color || "4caf50";
      if (color && !color.startsWith("#")) {
        color = "#" + color;
      }
      setLabelColor(color);

      // Set schema string
      if (editingEntityType.attributes_schema) {
        try {
          const schema =
            typeof editingEntityType.attributes_schema === "string"
              ? editingEntityType.attributes_schema
              : JSON.stringify(editingEntityType.attributes_schema, null, 2);

          // Validate JSON
          JSON.parse(schema);
          setAttributesSchema(schema);
          setJsonError("");
        } catch {
          setJsonError("Invalid JSON schema format");
          setAttributesSchema(
            JSON.stringify(
              {
                type: "object",
                properties: {},
                required: [],
              },
              null,
              2
            )
          );
        }
      }
    }
  }, [editingEntityType]);

  const mutation = useMutation({
    mutationFn: editingEntityType
      ? apiService.updateEntityType
      : apiService.createEntityType,
    onSuccess: () => {
      if (!editingEntityType) {
        // Reset form only for create mode
        setName("");
        setShortLabel("");
        setLabelColor("#4caf50");
        setAttributesSchema(
          JSON.stringify(
            {
              type: "object",
              properties: {},
              required: [],
            },
            null,
            2
          )
        );
        setJsonError("");
      }
      // Show success notification
      setShowSuccessSnackbar(true);

      // Invalidate and refetch entity types queries to refresh tables immediately
      queryClient.invalidateQueries({ queryKey: ["entity-types"] });
      queryClient.refetchQueries({ queryKey: ["entity-types"] });

      // Also invalidate entities queries since entity types affect entity displays
      queryClient.invalidateQueries({ queryKey: ["entities"] });
      queryClient.refetchQueries({ queryKey: ["entities"] });

      // Close modal if in edit mode (with a small delay to show the success message)
      if (editingEntityType && onClose) {
        setTimeout(() => {
          onClose();
        }, 1000); // 1 second delay to show success message
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate JSON schema
    if (jsonError) {
      return;
    }

    try {
      // Remove # prefix from labelColor for database storage
      const colorForDb = labelColor.startsWith("#")
        ? labelColor.slice(1)
        : labelColor;

      // Parse JSON string to object for API
      const schemaObject = JSON.parse(attributesSchema);

      const requestData: apiService.CreateEntityTypeRequest & {
        entity_type_id?: number;
      } = {
        name,
        attributes_schema: schemaObject,
        ...(shortLabel.trim() && { short_label: shortLabel.trim() }),
        ...(colorForDb.trim() && { label_color: colorForDb.trim() }),
      };

      // Add entity_type_id for updates
      if (editingEntityType) {
        requestData.entity_type_id = editingEntityType.entity_type_id;
      }
      mutation.mutate(requestData);
    } catch (error) {
      console.error("Error preparing request:", error);
    }
  };

  const isValidHexColor = (color: string) => {
    if (!color) return true; // Empty is valid (optional field)
    const hexPattern = /^#[0-9A-Fa-f]{6}$/;
    return hexPattern.test(color);
  };

  const handleJsonChange = (value: string) => {
    setAttributesSchema(value);
    try {
      JSON.parse(value);
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON syntax");
    }
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(attributesSchema);
      const formatted = JSON.stringify(parsed, null, 2);
      setAttributesSchema(formatted);
      setJsonError("");
    } catch {
      setJsonError("Cannot format: Invalid JSON syntax");
    }
  };

  const isJsonAlreadyFormatted = () => {
    try {
      const parsed = JSON.parse(attributesSchema);
      const formatted = JSON.stringify(parsed, null, 2);
      return attributesSchema === formatted;
    } catch {
      return false; // Invalid JSON, so not formatted
    }
  };

  const canSubmit =
    name.trim() &&
    !jsonError &&
    isValidHexColor(labelColor) &&
    !mutation.isPending;

  return (
    <Box
      sx={{ height: "100%", display: "flex", flexDirection: "column", p: 3 }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography variant="h4">
            {editingEntityType ? "Edit Entity Type" : "Create Entity Type"}
          </Typography>
          {editingEntityType && (
            <Chip
              label={`ID: ${editingEntityType.entity_type_id}`}
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

        {mutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error:{" "}
            {mutation.error?.message ||
              `Failed to ${
                editingEntityType ? "update" : "create"
              } entity type`}
          </Alert>
        )}

        {mutation.isSuccess && !editingEntityType && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Entity type created successfully!
          </Alert>
        )}

        <form
          onSubmit={handleSubmit}
          style={{ height: "100%", display: "flex", flexDirection: "column" }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 3,
              flex: 1,
              overflow: "auto",
              pr: 1,
            }}
          >
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
              disabled={mutation.isPending}
            />

            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
              <TextField
                label="Short Label"
                value={shortLabel}
                onChange={(e) => setShortLabel(e.target.value)}
                disabled={mutation.isPending}
                inputProps={{ maxLength: 10 }}
                sx={{ flex: 1 }}
              />

              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mt: 1,
                  position: "relative",
                }}
              >
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    backgroundColor: labelColor,
                    border: "2px solid #ccc",
                    borderRadius: "8px",
                    cursor: "pointer",
                    flexShrink: 0,
                    transition: "border-color 0.2s",
                    "&:hover": {
                      borderColor: "#999",
                    },
                  }}
                  onClick={() => setShowColorPicker(!showColorPicker)}
                />
                <Typography variant="caption" color="text.secondary">
                  Click to change color
                </Typography>
                {showColorPicker && (
                  <Box
                    sx={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      mt: 1,
                      p: 2,
                      border: "1px solid #ccc",
                      borderRadius: 1,
                      backgroundColor: "white",
                      boxShadow: 3,
                      zIndex: 1000,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ mb: 1, display: "block" }}
                    >
                      Select color:
                    </Typography>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: "repeat(4, 1fr)",
                        gap: 0.5,
                        maxWidth: 200,
                      }}
                    >
                      {COLOR_PALETTE.map((color) => (
                        <Box
                          key={color}
                          sx={{
                            width: 40,
                            height: 40,
                            backgroundColor: color,
                            border:
                              labelColor === color
                                ? "3px solid #000"
                                : "2px solid #ccc",
                            borderRadius: "4px",
                            cursor: "pointer",
                            transition: "all 0.2s",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            "&:hover": {
                              borderColor: "#666",
                              transform: "scale(1.05)",
                            },
                          }}
                          onClick={() => {
                            setLabelColor(color);
                            setShowColorPicker(false);
                          }}
                        >
                          {labelColor === color && (
                            <Typography
                              sx={{
                                color: "white",
                                fontSize: "16px",
                                fontWeight: "bold",
                                textShadow: "1px 1px 2px rgba(0,0,0,0.7)",
                              }}
                            >
                              ✓
                            </Typography>
                          )}
                        </Box>
                      ))}
                    </Box>
                    <Box sx={{ mt: 1, textAlign: "center" }}>
                      <Button
                        size="small"
                        onClick={() => setShowColorPicker(false)}
                      >
                        Close
                      </Button>
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>

            <FormControl fullWidth>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1,
                }}
              >
                <FormLabel>Attributes Schema (JSON) *</FormLabel>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={formatJson}
                  disabled={mutation.isPending || isJsonAlreadyFormatted()}
                  sx={{ minWidth: "auto", px: 2 }}
                >
                  Format JSON
                </Button>
              </Box>
              <Box
                sx={{
                  border: jsonError ? "2px solid #f44336" : "1px solid #ccc",
                  borderRadius: 1,
                  height: 300,
                  overflow: "auto",
                  backgroundColor: "#fafafa",
                }}
              >
                <AceEditor
                  mode="json"
                  theme="github"
                  value={attributesSchema}
                  onChange={handleJsonChange}
                  name="json-schema-editor"
                  width="100%"
                  height="300px"
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
                    useWorker: false, // Disable worker for better compatibility
                  }}
                  style={{
                    backgroundColor: "#fafafa",
                    borderRadius: "4px",
                  }}
                />
              </Box>
              {jsonError && (
                <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                  {jsonError}
                </Typography>
              )}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1 }}
              >
                JSON schema defining the attributes for this entity type. Edit
                directly in the text editor above.
              </Typography>
            </FormControl>

            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 2,
                mt: 2,
                flexShrink: 0,
              }}
            >
              {editingEntityType && onClose && (
                <Button
                  variant="outlined"
                  onClick={onClose}
                  disabled={mutation.isPending}
                >
                  Cancel
                </Button>
              )}
              <Button type="submit" variant="contained" disabled={!canSubmit}>
                {mutation.isPending ? (
                  <>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    {editingEntityType ? "Updating..." : "Creating..."}
                  </>
                ) : editingEntityType ? (
                  "Update Entity Type"
                ) : (
                  "Create Entity Type"
                )}
              </Button>
            </Box>
          </Box>
        </form>
      </Paper>

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
          {editingEntityType
            ? "Entity type updated successfully!"
            : "Entity type created successfully!"}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default EntityTypeForm;
