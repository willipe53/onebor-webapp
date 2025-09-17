import React, { useMemo } from "react";
import { Box, Typography, CircularProgress, Button, Chip } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import * as apiService from "../services/api";

const EntityTypesTable: React.FC = () => {
  // Fetch entity types
  const {
    data: rawData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => apiService.queryEntityTypes({}),
  });

  // Transform array data to objects if needed
  const data = React.useMemo(() => {
    if (!rawData) return [];

    // Check if data is already in object format
    if (
      Array.isArray(rawData) &&
      rawData.length > 0 &&
      typeof rawData[0] === "object" &&
      "entity_type_id" in rawData[0]
    ) {
      return rawData;
    }

    // Transform array format [id, name, schema] to object format
    if (Array.isArray(rawData)) {
      return rawData.map((row: any) => {
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

    return rawData;
  }, [rawData]);

  const formatSchema = (schema: any) => {
    if (!schema || typeof schema !== "object") return "None";

    try {
      const properties = schema.properties || {};
      const propNames = Object.keys(properties);
      if (propNames.length === 0) return "None";

      return propNames
        .map((prop) => {
          const propDef = properties[prop];
          const type = propDef.type || "unknown";
          const format = propDef.format ? `:${propDef.format}` : "";
          return `${prop}(${type}${format})`;
        })
        .join(", ");
    } catch {
      return "Invalid Schema";
    }
  };

  // Define DataGrid columns
  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: "entity_type_id",
        headerName: "ID",
        width: 100,
        renderCell: (params: GridRenderCellParams) => (
          <Chip label={params.value} size="small" />
        ),
      },
      {
        field: "name",
        headerName: "Name",
        width: 200,
        flex: 1,
      },
      {
        field: "attributes_schema",
        headerName: "Schema Properties",
        width: 400,
        flex: 2,
        renderCell: (params: GridRenderCellParams) => (
          <Typography
            variant="body2"
            sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
          >
            {formatSchema(params.value)}
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
          Error loading entity types
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

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Entity Types
      </Typography>

      {/* Data Grid */}
      <Box sx={{ height: 600, width: "100%" }}>
        <DataGrid
          rows={data || []}
          columns={columns}
          getRowId={(row) => row.entity_type_id}
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

export default EntityTypesTable;
