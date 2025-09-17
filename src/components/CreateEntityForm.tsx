import React, { useState } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as apiService from "../services/api";

const CreateEntityForm: React.FC = () => {
  const [name, setName] = useState("");
  const [entityTypeId, setEntityTypeId] = useState<number | "">("");
  const [parentEntityId, setParentEntityId] = useState<number | "">("");
  const [attributes, setAttributes] = useState("{}");

  const queryClient = useQueryClient();

  // Fetch entity types for the dropdown
  const { data: entityTypesData, isLoading: entityTypesLoading } = useQuery({
    queryKey: ["entity-types", { page: 1, page_size: 100 }],
    queryFn: () => apiService.queryEntityTypes({ page: 1, page_size: 100 }),
  });

  const mutation = useMutation({
    mutationFn: apiService.createEntity,
    onSuccess: () => {
      // Reset form
      setName("");
      setEntityTypeId("");
      setParentEntityId("");
      setAttributes("{}");
      // Invalidate entities queries to refresh tables
      queryClient.invalidateQueries({ queryKey: ["entities"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (entityTypeId === "") return;

    try {
      const parsedAttributes = JSON.parse(attributes);
      const requestData: apiService.CreateEntityRequest = {
        name,
        entity_type_id: entityTypeId as number,
        parent_entity_id:
          parentEntityId === "" ? null : (parentEntityId as number),
        attributes: parsedAttributes,
      };
      mutation.mutate(requestData);
    } catch (error) {
      console.error("Invalid JSON in attributes:", error);
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
    name.trim() &&
    entityTypeId !== "" &&
    isValidJson(attributes) &&
    !mutation.isPending;

  return (
    <Box sx={{ maxWidth: 600, mx: "auto", p: 3 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Create Entity
        </Typography>

        {mutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error: {mutation.error?.message || "Failed to create entity"}
          </Alert>
        )}

        {mutation.isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Entity created successfully!
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

            <FormControl
              fullWidth
              required
              disabled={mutation.isPending || entityTypesLoading}
            >
              <InputLabel>Entity Type</InputLabel>
              <Select
                value={entityTypeId}
                onChange={(e) => setEntityTypeId(e.target.value as number)}
                label="Entity Type"
              >
                {entityTypesData?.entity_types.map((type) => (
                  <MenuItem
                    key={type.entity_type_id}
                    value={type.entity_type_id}
                  >
                    {type.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Parent Entity ID (optional)"
              type="number"
              value={parentEntityId}
              onChange={(e) =>
                setParentEntityId(
                  e.target.value === "" ? "" : Number(e.target.value)
                )
              }
              fullWidth
              disabled={mutation.isPending}
              helperText="Leave empty if this entity has no parent"
            />

            <TextField
              label="Attributes (JSON)"
              value={attributes}
              onChange={(e) => setAttributes(e.target.value)}
              multiline
              rows={6}
              required
              fullWidth
              disabled={mutation.isPending}
              error={!isValidJson(attributes)}
              helperText={
                !isValidJson(attributes)
                  ? "Invalid JSON format"
                  : "JSON object with entity attributes"
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
                "Create Entity"
              )}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
};

export default CreateEntityForm;
