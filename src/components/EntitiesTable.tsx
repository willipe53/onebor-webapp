import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  TextField,
  Button,
  Stack,
  MenuItem,
  Chip,
  Modal,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type {
  GridColDef,
  GridRenderCellParams,
  GridRowParams,
} from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import * as apiService from "../services/api";
import EntityForm from "./EntityForm";

const EntitiesTable: React.FC = () => {
  const { userId } = useAuth();

  // Get current user's database ID
  const { data: currentUser } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
    select: (data) => data[0], // Get first user from array
  });

  const [filters, setFilters] = useState<
    Partial<apiService.QueryEntitiesRequest>
  >({});
  const [nameFilter, setNameFilter] = useState("");
  const [entityIdFilter, setEntityIdFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [parentEntityFilter, setParentEntityFilter] = useState("");
  const [editingEntity, setEditingEntity] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch entities
  const {
    data: rawEntitiesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["entities", filters, currentUser?.user_id],
    queryFn: () =>
      apiService.queryEntities({ ...filters, user_id: currentUser!.user_id }),
    enabled: !!currentUser?.user_id, // Only run query when user data is loaded
  });

  // Transform array data to objects if needed
  const entitiesData = React.useMemo(() => {
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
            attributes: row[4], // Don't parse here, let formatAttributes handle it
          };
        }
        return row;
      });
    }

    return rawEntitiesData;
  }, [rawEntitiesData]);

  // Fetch entity types for filter dropdown
  const { data: rawEntityTypesData } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => apiService.queryEntityTypes({}),
  });

  // Transform entity types data for dropdown
  const entityTypesData = React.useMemo(() => {
    if (!rawEntityTypesData) return [];

    // Check if data is already in object format
    if (
      Array.isArray(rawEntityTypesData) &&
      rawEntityTypesData.length > 0 &&
      typeof rawEntityTypesData[0] === "object" &&
      "entity_type_id" in rawEntityTypesData[0]
    ) {
      return rawEntityTypesData;
    }

    // Transform array format [id, name, schema, short_label, label_color] to object format
    if (Array.isArray(rawEntityTypesData)) {
      return rawEntityTypesData.map((row: any) => {
        if (Array.isArray(row) && row.length >= 3) {
          return {
            entity_type_id: row[0],
            name: row[1],
            attributes_schema:
              typeof row[2] === "string" ? JSON.parse(row[2]) : row[2],
            short_label: row[3] || null,
            label_color: row[4] || null,
          };
        }
        return row;
      });
    }

    return rawEntityTypesData;
  }, [rawEntityTypesData]);

  const formatAttributes = (attributes: any) => {
    if (!attributes) return "None";

    let parsedAttributes;

    // Handle different data types - parse to object first
    if (typeof attributes === "string") {
      try {
        parsedAttributes = JSON.parse(attributes);
      } catch {
        return `Invalid JSON: ${attributes.substring(0, 50)}...`;
      }
    } else if (typeof attributes === "object") {
      parsedAttributes = attributes;
    } else {
      return String(attributes);
    }

    try {
      const entries = Object.entries(parsedAttributes);
      if (entries.length === 0) return "None";

      return entries
        .map(([key, value]) => {
          // Determine the type of the value for better formatting
          let valueType: string = typeof value;
          let displayValue = String(value);

          // Handle special cases
          if (value === null) {
            valueType = "null";
            displayValue = "null";
          } else if (Array.isArray(value)) {
            valueType = "array";
            displayValue = `[${value.length} items]`;
          } else if (typeof value === "object") {
            valueType = "object";
            displayValue = "{...}";
          } else if (typeof value === "string" && value.length > 20) {
            displayValue = `${value.substring(0, 20)}...`;
          }

          return `${key}(${valueType}): ${displayValue}`;
        })
        .join(", ");
    } catch {
      return "Invalid attributes";
    }
  };

  // Define DataGrid columns
  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: "entity_id",
        headerName: "ID",
        renderCell: (params: GridRenderCellParams) => (
          <Typography variant="body2" sx={{ fontWeight: "500" }}>
            {params.value}
          </Typography>
        ),
      },
      {
        field: "short_label",
        headerName: "Type",
        renderCell: (params: GridRenderCellParams) => {
          // Find the entity type for this entity to get its short_label and color
          const entityType = entityTypesData?.find(
            (type) => type.entity_type_id === params.row.entity_type_id
          );
          const shortLabel = entityType?.short_label;
          const labelColor = entityType?.label_color;
          const colorValue = labelColor?.startsWith("#")
            ? labelColor
            : labelColor
            ? `#${labelColor}`
            : "#000000";

          return shortLabel ? (
            <Typography
              variant="body2"
              sx={{
                fontWeight: "bold",
                color: colorValue,
              }}
            >
              {shortLabel}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">
              —
            </Typography>
          );
        },
      },
      {
        field: "name",
        headerName: "Name",
      },
      {
        field: "parent_entity_id",
        headerName: "Parent",
        renderCell: (params: GridRenderCellParams) => {
          if (!params.value) {
            return (
              <Typography variant="body2" color="text.secondary">
                —
              </Typography>
            );
          }

          // Find the parent entity
          const parentEntity = entitiesData?.find(
            (entity) => entity.entity_id === params.value
          );

          if (!parentEntity) {
            return (
              <Typography variant="body2" color="text.secondary">
                Unknown
              </Typography>
            );
          }

          // Find the parent's entity type for color information
          const parentEntityType = entityTypesData?.find(
            (type) => type.entity_type_id === parentEntity.entity_type_id
          );
          const parentShortLabel = parentEntityType?.short_label;
          const parentLabelColor = parentEntityType?.label_color;
          const parentColorValue = parentLabelColor?.startsWith("#")
            ? parentLabelColor
            : parentLabelColor
            ? `#${parentLabelColor}`
            : "#000000";

          const chipLabel = parentShortLabel
            ? `${parentShortLabel} ${parentEntity.name}`
            : parentEntity.name;

          return (
            <Chip
              label={chipLabel}
              size="small"
              sx={{
                backgroundColor: parentColorValue + "20", // 20% opacity background
                color: parentColorValue,
                fontWeight: "bold",
                "& .MuiChip-label": {
                  fontWeight: "bold",
                },
              }}
            />
          );
        },
      },
      {
        field: "attributes",
        headerName: "Attributes",
        flex: 1,
        renderCell: (params: GridRenderCellParams) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: "monospace",
              fontSize: "0.75rem",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              lineHeight: 1.2,
              padding: "4px 0",
            }}
          >
            {formatAttributes(params.value)}
          </Typography>
        ),
      },
    ],
    [entityTypesData, entitiesData]
  );

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "400px",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error" variant="h6" gutterBottom>
          Error loading entities
        </Typography>
        <Typography color="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Unknown error"}
        </Typography>
        <Button variant="contained" onClick={() => refetch()}>
          Retry
        </Button>
      </Box>
    );
  }

  const handleFilter = () => {
    const newFilters: Partial<apiService.QueryEntitiesRequest> = {};
    if (entityIdFilter) newFilters.entity_id = parseInt(entityIdFilter);
    if (nameFilter) newFilters.name = nameFilter;
    if (entityTypeFilter)
      newFilters.entity_type_id = parseInt(entityTypeFilter);
    if (parentEntityFilter)
      newFilters.parent_entity_id = parseInt(parentEntityFilter);
    setFilters({ ...newFilters, user_id: currentUser!.user_id });
  };

  const clearFilters = () => {
    setFilters({ user_id: currentUser!.user_id });
    setNameFilter("");
    setEntityIdFilter("");
    setEntityTypeFilter("");
    setParentEntityFilter("");
  };

  const handleRowClick = (params: GridRowParams) => {
    setEditingEntity(params.row);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingEntity(null);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Entities
      </Typography>

      {/* Filters */}
      <Box sx={{ mb: 3, p: 2, border: "1px solid #ddd", borderRadius: 1 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Filters
        </Typography>
        <Stack spacing={2}>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Entity ID"
              value={entityIdFilter}
              onChange={(e) => setEntityIdFilter(e.target.value)}
              size="small"
              sx={{ minWidth: 120 }}
            />
            <TextField
              label="Name"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              size="small"
              sx={{ minWidth: 200 }}
            />
          </Stack>
          <Stack direction="row" spacing={2}>
            <TextField
              select
              label="Entity Type"
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
              size="small"
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="">All Types</MenuItem>
              {(entityTypesData || []).map((type) => (
                <MenuItem key={type.entity_type_id} value={type.entity_type_id}>
                  {type.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Parent Entity ID"
              value={parentEntityFilter}
              onChange={(e) => setParentEntityFilter(e.target.value)}
              size="small"
              sx={{ minWidth: 150 }}
            />
          </Stack>
          <Stack direction="row" spacing={2}>
            <Button variant="contained" onClick={handleFilter}>
              Apply Filters
            </Button>
            <Button variant="outlined" onClick={clearFilters}>
              Clear Filters
            </Button>
            <Button variant="outlined" onClick={() => refetch()}>
              Refresh Data
            </Button>
          </Stack>
        </Stack>
      </Box>

      {/* Data Grid */}
      <Box sx={{ height: 600, width: "100%" }}>
        <DataGrid
          rows={entitiesData || []}
          columns={columns}
          getRowId={(row) => row.entity_id}
          pagination
          pageSizeOptions={[25, 50, 100]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 25 },
            },
          }}
          disableRowSelectionOnClick
          onRowClick={handleRowClick}
          getRowHeight={() => "auto"}
          sx={{
            "& .MuiDataGrid-cell": {
              fontSize: "0.875rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-start",
            },
            "& .MuiDataGrid-columnHeaders": {
              backgroundColor: "rgba(25, 118, 210, 0.15) !important", // Slightly more visible blue
              borderBottom: "1px solid rgba(25, 118, 210, 0.2) !important",
            },
            "& .MuiDataGrid-columnHeader": {
              backgroundColor: "rgba(25, 118, 210, 0.15) !important",
              display: "flex",
              alignItems: "center",
            },
          }}
        />
      </Box>

      {/* Edit Modal */}
      <Modal
        open={isModalOpen}
        onClose={handleCloseModal}
        aria-labelledby="edit-entity-modal"
        aria-describedby="edit-entity-form"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "90%",
            maxWidth: 800,
            maxHeight: "90vh",
            overflow: "auto",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          {editingEntity && (
            <EntityForm
              editingEntity={editingEntity}
              onClose={handleCloseModal}
            />
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default EntitiesTable;
