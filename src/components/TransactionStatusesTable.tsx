import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Button,
  Modal,
  Tooltip,
  IconButton,
} from "@mui/material";
import { Add, InfoOutlined } from "@mui/icons-material";
import { DataGrid } from "@mui/x-data-grid";
import type {
  GridColDef,
  GridRenderCellParams,
  GridRowParams,
} from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";
import * as apiService from "../services/api";
import type {
  QueryTransactionStatusesResponse,
  TransactionStatus,
} from "../services/api";
import TransactionStatusForm from "./TransactionStatusForm";

const TransactionStatusesTable: React.FC = () => {
  const [editingTransactionStatus, setEditingTransactionStatus] =
    useState<TransactionStatus | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch transaction statuses
  const {
    data: rawData,
    isLoading,
    error,
    refetch,
  } = useQuery<QueryTransactionStatusesResponse>({
    queryKey: ["transaction-statuses"],
    queryFn: async () => {
      try {
        const result = await apiService.queryTransactionStatuses({});
        return result;
      } catch (err) {
        console.error("❌ TransactionStatusesTable - API call failed:", err);
        throw err;
      }
    },
  });

  // Use the data directly since it's already an array of TransactionStatus
  const data = rawData || [];

  // Get current user for primary client group (simplified approach)
  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiService.queryUsers({ sub: "current" }),
    select: (data) => data[0],
  });

  // Get primary client group details
  const { data: primaryClientGroup } = useQuery({
    queryKey: ["primary-client-group", currentUser?.primary_client_group_id],
    queryFn: () =>
      apiService.queryClientGroups({
        client_group_id: currentUser!.primary_client_group_id!,
      }),
    enabled: !!currentUser?.primary_client_group_id,
    select: (data) => data[0],
  });

  // Define DataGrid columns
  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: "transaction_status_id",
        headerName: "ID",
        width: 100,
        renderCell: (params: GridRenderCellParams) => (
          <Typography variant="body2" sx={{ fontWeight: "500" }}>
            {params.value}
          </Typography>
        ),
      },
      {
        field: "name",
        headerName: "Name",
        flex: 1,
        minWidth: 200,
      },
    ],
    []
  );

  const handleRowClick = (params: GridRowParams) => {
    setEditingTransactionStatus(params.row);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTransactionStatus(null);
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
          Error loading transaction statuses
        </Typography>
        <Typography color="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Unknown error"}
        </Typography>
        <Typography variant="body2" sx={{ mb: 2, color: "text.secondary" }}>
          This is likely a backend API issue. The /get_transaction_statuses
          endpoint is returning an error.
        </Typography>
        <Typography variant="body2" sx={{ mb: 3, color: "text.secondary" }}>
          💡 <strong>Possible causes:</strong> Database constraint violations,
          Lambda function errors, or API gateway timeouts.
        </Typography>
        <Button variant="contained" onClick={() => refetch()} sx={{ mr: 2 }}>
          Retry
        </Button>
        <Button
          variant="outlined"
          onClick={() => {
            console.log("TransactionStatusesTable error details:", error);
            alert("Check browser console for detailed error information");
          }}
        >
          Show Debug Info
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Typography variant="h5">Transaction Statuses</Typography>
        <Tooltip
          title="Transaction Statuses define the processing state of transactions (Pending, Processed, Failed, etc.)."
          placement="right"
          arrow
        >
          <IconButton size="small" sx={{ color: "text.secondary" }}>
            <InfoOutlined fontSize="small" />
          </IconButton>
        </Tooltip>
        <Button
          variant="contained"
          color="success"
          size="small"
          startIcon={<Add />}
          onClick={() => {
            setEditingTransactionStatus(null); // Set null for new transaction status
            setIsModalOpen(true);
          }}
          sx={{
            borderRadius: "20px",
            textTransform: "none",
            fontWeight: 600,
          }}
        >
          New
        </Button>
      </Box>

      {/* Data Grid */}
      <Box sx={{ height: 600, width: "100%" }}>
        {data.length === 0 && !isLoading ? (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No transaction statuses found
              <br />
              No transaction statuses exist for{" "}
              {primaryClientGroup?.name || "this client group"}
              <br />
              Click "New" to create one for{" "}
              {primaryClientGroup?.name || "this client group"}.
            </Typography>
          </Box>
        ) : (
          <DataGrid
            rows={data || []}
            columns={columns}
            getRowId={(row) => row.transaction_status_id}
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
                backgroundColor: "#f5f5f5 !important", // Solid light gray background
                borderBottom: "1px solid rgba(25, 118, 210, 0.2) !important",
              },
              "& .MuiDataGrid-columnHeader": {
                backgroundColor: "#f5f5f5 !important", // Solid light gray background
                display: "flex",
                alignItems: "center",
              },
            }}
          />
        )}
      </Box>

      {/* Edit Modal */}
      <Modal
        open={isModalOpen}
        onClose={handleCloseModal}
        aria-labelledby="edit-transaction-status-modal"
        aria-describedby="edit-transaction-status-form"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "90%",
            maxWidth: 500,
            height: "auto",
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          <TransactionStatusForm
            editingTransactionStatus={editingTransactionStatus || undefined}
            onClose={handleCloseModal}
          />
        </Box>
      </Modal>
    </Box>
  );
};

export default TransactionStatusesTable;
