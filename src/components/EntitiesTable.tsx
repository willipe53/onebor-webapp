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
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import * as apiService from "../services/api";

const EntitiesTable: React.FC = () => {
  const [filters, setFilters] = useState<apiService.QueryEntitiesRequest>({});
  const [nameFilter, setNameFilter] = useState("");
  const [entityIdFilter, setEntityIdFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [parentEntityFilter, setParentEntityFilter] = useState("");

  // Fetch entities
  const {
    data: rawEntitiesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["entities", filters],
    queryFn: () => apiService.queryEntities(filters),
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
            attributes:
              typeof row[4] === "string" ? JSON.parse(row[4]) : row[4],
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

    // Transform array format [id, name, schema] to object format
    if (Array.isArray(rawEntityTypesData)) {
      return rawEntityTypesData.map((row: any) => {
        if (Array.isArray(row) && row.length >= 3) {
          return {
            entity_type_id: row[0],
            name: row[1],
            attributes_schema:
              typeof row[2] === "string" ? JSON.parse(row[2]) : row[2],
          };
        }
        return row;
      });
    }

    return rawEntityTypesData;
  }, [rawEntityTypesData]);

  const formatAttributes = (attributes: any) => {
    if (!attributes || typeof attributes !== "object") return "None";

    try {
      const parsed =
        typeof attributes === "string" ? JSON.parse(attributes) : attributes;
      const entries = Object.entries(parsed);
      if (entries.length === 0) return "None";

      return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
    } catch {
      return String(attributes);
    }
  };

  // Define DataGrid columns
  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: "entity_id",
        headerName: "ID",
        width: 100,
        renderCell: (params: GridRenderCellParams) => (
          <Chip label={params.value} size="small" />
        ),
      },
      {
        field: "name",
        headerName: "Name",
        width: 250,
        flex: 1,
      },
      {
        field: "entity_type_id",
        headerName: "Type ID",
        width: 100,
        renderCell: (params: GridRenderCellParams) => (
          <Chip label={params.value} size="small" color="primary" />
        ),
      },
      {
        field: "parent_entity_id",
        headerName: "Parent ID",
        width: 120,
        renderCell: (params: GridRenderCellParams) =>
          params.value ? (
            <Chip label={params.value} size="small" color="secondary" />
          ) : (
            <Typography variant="caption" color="text.secondary">
              None
            </Typography>
          ),
      },
      {
        field: "attributes",
        headerName: "Attributes",
        width: 300,
        flex: 1,
        renderCell: (params: GridRenderCellParams) => (
          <Typography
            variant="body2"
            sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
          >
            {formatAttributes(params.value)}
          </Typography>
        ),
      },
    ],
    []
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
    const newFilters: apiService.QueryEntitiesRequest = {};
    if (entityIdFilter) newFilters.entity_id = parseInt(entityIdFilter);
    if (nameFilter) newFilters.name = nameFilter;
    if (entityTypeFilter)
      newFilters.entity_type_id = parseInt(entityTypeFilter);
    if (parentEntityFilter)
      newFilters.parent_entity_id = parseInt(parentEntityFilter);
    setFilters(newFilters);
  };

  const clearFilters = () => {
    setFilters({});
    setNameFilter("");
    setEntityIdFilter("");
    setEntityTypeFilter("");
    setParentEntityFilter("");
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
          sx={{
            "& .MuiDataGrid-cell": {
              fontSize: "0.875rem",
            },
            "& .MuiDataGrid-columnHeaders": {
              backgroundColor: "rgba(0, 0, 0, 0.04)",
            },
          }}
        />
      </Box>
    </Box>
  );
};

export default EntitiesTable;
