import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Button,
  Modal,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type {
  GridColDef,
  GridRenderCellParams,
  GridRowParams,
} from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import * as apiService from "../services/api";
import EntityTypeForm from "./EntityTypeForm";

const EntityTypesTable: React.FC = () => {
  const [editingEntityType, setEditingEntityType] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

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

    // Transform array format [id, name, schema, short_label, label_color] to object format
    if (Array.isArray(rawData)) {
      return rawData.map((row: any) => {
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
          // Get the label_color from the same row
          const labelColor = params.row.label_color;
          const colorValue = labelColor?.startsWith("#")
            ? labelColor
            : labelColor
            ? `#${labelColor}`
            : "#000000";

          return params.value ? (
            <Typography
              variant="body2"
              sx={{
                fontWeight: "bold",
                color: colorValue,
              }}
            >
              {params.value}
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
        field: "attributes_schema",
        headerName: "Schema Properties",
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
            {formatSchema(params.value)}
          </Typography>
        ),
      },
    ],
    []
  );

  const handleRowClick = (params: GridRowParams) => {
    setEditingEntityType(params.row);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingEntityType(null);
  };

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
      {/* Updated header styling - force refresh */}
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
          onRowClick={handleRowClick}
          getRowHeight={() => "auto"}
          sx={{
            "& .MuiDataGrid-cell": {
              fontSize: "0.875rem",
              display: "flex",
              alignItems: "center",
              lineHeight: "unset !important",
              maxHeight: "none !important",
              whiteSpace: "unset",
            },
            "& .MuiDataGrid-row": {
              maxHeight: "none !important",
            },
            "& .MuiDataGrid-renderingZone": {
              maxHeight: "none !important",
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
        aria-labelledby="edit-entity-type-modal"
        aria-describedby="edit-entity-type-form"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "90%",
            maxWidth: 700,
            height: "90vh",
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          {editingEntityType && (
            <EntityTypeForm
              editingEntityType={editingEntityType}
              onClose={handleCloseModal}
            />
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default EntityTypesTable;
