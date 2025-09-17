import React, { useState } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as apiService from "../services/api";

const CreateEntityTypeForm: React.FC = () => {
  const [name, setName] = useState("");
  const [attributesSchema, setAttributesSchema] = useState(
    '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}'
  );

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: apiService.createEntityType,
    onSuccess: () => {
      // Reset form
      setName("");
      setAttributesSchema(
        '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}'
      );
      // Invalidate entity types queries to refresh tables
      queryClient.invalidateQueries({ queryKey: ["entity-types"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const schema = JSON.parse(attributesSchema);
      const requestData: apiService.CreateEntityTypeRequest = {
        name,
        attributes_schema: schema,
      };
      mutation.mutate(requestData);
    } catch (error) {
      console.error("Invalid JSON in attributes schema:", error);
    }
  };

  const isValidJson = (str: string) => {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  };

  const canSubmit =
    name.trim() && isValidJson(attributesSchema) && !mutation.isPending;

  return (
    <Box sx={{ maxWidth: 600, mx: "auto", p: 3 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Create Entity Type
        </Typography>

        {mutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error: {mutation.error?.message || "Failed to create entity type"}
          </Alert>
        )}

        {mutation.isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Entity type created successfully!
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
              disabled={mutation.isPending}
            />

            <TextField
              label="Attributes Schema (JSON)"
              value={attributesSchema}
              onChange={(e) => setAttributesSchema(e.target.value)}
              multiline
              rows={10}
              required
              fullWidth
              disabled={mutation.isPending}
              error={!isValidJson(attributesSchema)}
              helperText={
                !isValidJson(attributesSchema)
                  ? "Invalid JSON format"
                  : "JSON schema defining the attributes for this entity type"
              }
              sx={{ fontFamily: "monospace" }}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={!canSubmit}
              fullWidth
              sx={{ mt: 2 }}
            >
              {mutation.isPending ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Creating...
                </>
              ) : (
                "Create Entity Type"
              )}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
};

export default CreateEntityTypeForm;
