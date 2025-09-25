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
  Autocomplete,
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
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import * as apiService from "../services/api";
import DynamicTransactionForm from "./DynamicTransactionForm";
import TransactionTypesTable from "./TransactionTypesTable";
import TransactionStatusesTable from "./TransactionStatusesTable";
import { formatDatabaseTimestamp } from "../utils";

interface TransactionsTableProps {
  groupSelectionMode?: {
    clientGroupId: number;
    clientGroupName: string;
    onFinish: (selectedTransactionIds: number[]) => void;
    onCancel: () => void;
  };
}

const TransactionsTable: React.FC<TransactionsTableProps> = ({
  groupSelectionMode,
}) => {
  const { userId } = useAuth();
  const queryClient = useQueryClient();

  // Get current user's database ID
  const { data: currentUser } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
    select: (data) => data[0], // Get first user from array
  });

  // Get primary client group for display
  const { data: primaryClientGroup } = useQuery({
    queryKey: ["primary-client-group", currentUser?.primary_client_group_id],
    queryFn: () =>
      apiService.queryClientGroups({
        client_group_id: currentUser!.primary_client_group_id!,
      }),
    enabled: !!currentUser?.primary_client_group_id,
    select: (data) => data[0],
  });

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<
    apiService.Transaction | undefined
  >(undefined);
  const [isTransactionTypesModalOpen, setIsTransactionTypesModalOpen] =
    useState(false);
  const [isTransactionStatusesModalOpen, setIsTransactionStatusesModalOpen] =
    useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTransactionType, setSelectedTransactionType] = useState<
    number | null
  >(null);
  const [selectedTransactionStatus, setSelectedTransactionStatus] = useState<
    number | null
  >(null);

  // Fetch transactions
  const {
    data: rawTransactionsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      "transactions",
      "client-group",
      currentUser?.primary_client_group_id,
      searchTerm,
      selectedTransactionType,
      selectedTransactionStatus,
    ],
    queryFn: async () => {
      if (!currentUser?.user_id) {
        throw new Error("No user ID available");
      }

      const queryParams: apiService.QueryTransactionsRequest = {
        user_id: currentUser.user_id,
        client_group_id: currentUser.primary_client_group_id,
      };

      console.log(
        "🔍 TransactionsTable - Querying transactions with params:",
        queryParams
      );

      try {
        const result = await apiService.queryTransactions(queryParams);
        console.log("🔍 TransactionsTable - API result:", result);
        return result;
      } catch (error) {
        console.error("🔍 TransactionsTable - API error:", error);
        throw error;
      }
    },
    enabled: !!currentUser?.user_id && !!currentUser?.primary_client_group_id,
    staleTime: 0,
    refetchOnMount: true,
  });

  // Fetch transaction types for filter
  const { data: transactionTypes } = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => apiService.queryTransactionTypes({}),
  });

  // Fetch transaction statuses for filter
  const { data: transactionStatuses } = useQuery({
    queryKey: ["transaction-statuses"],
    queryFn: () => apiService.queryTransactionStatuses({}),
  });

  // Fetch entities for display
  const { data: entities } = useQuery({
    queryKey: ["entities", currentUser?.primary_client_group_id],
    queryFn: () =>
      apiService.queryEntities({
        user_id: currentUser!.user_id,
        client_group_id: currentUser!.primary_client_group_id,
      }),
    enabled: !!currentUser?.user_id && !!currentUser?.primary_client_group_id,
  });

  // Process transactions data
  const transactionsData = useMemo(() => {
    if (!rawTransactionsData || !entities) return [];

    let processedData = rawTransactionsData.map((transaction) => {
      // Find entity names
      const portfolioEntity = entities.find(
        (e) => e.entity_id === transaction.portfolio_entity_id
      );
      const counterpartyEntity = entities.find(
        (e) => e.entity_id === transaction.counterparty_entity_id
      );
      const instrumentEntity = entities.find(
        (e) => e.entity_id === transaction.instrument_entity_id
      );

      // Find transaction type and status names
      const transactionType = transactionTypes?.find(
        (t) => t.transaction_type_id === transaction.transaction_type_id
      );
      const transactionStatus = transactionStatuses?.find(
        (s) => s.transaction_status_id === transaction.transaction_status_id
      );

      return {
        id: transaction.transaction_id,
        transaction_id: transaction.transaction_id,
        portfolio_entity_id: transaction.portfolio_entity_id,
        portfolio_entity_name:
          portfolioEntity?.name || `Entity ${transaction.portfolio_entity_id}`,
        counterparty_entity_id: transaction.counterparty_entity_id,
        counterparty_entity_name:
          counterpartyEntity?.name ||
          `Entity ${transaction.counterparty_entity_id}`,
        instrument_entity_id: transaction.instrument_entity_id,
        instrument_entity_name:
          instrumentEntity?.name ||
          `Entity ${transaction.instrument_entity_id}`,
        properties: transaction.properties,
        transaction_type_id: transaction.transaction_type_id,
        transaction_type_name:
          transactionType?.name || `Type ${transaction.transaction_type_id}`,
        transaction_status_id: transaction.transaction_status_id,
        transaction_status_name:
          transactionStatus?.name ||
          `Status ${transaction.transaction_status_id}`,
        update_date: transaction.update_date,
        updated_user_id: transaction.updated_user_id,
      };
    });

    // Apply filters
    if (searchTerm) {
      processedData = processedData.filter(
        (transaction) =>
          transaction.party_entity_name
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          transaction.counterparty_entity_name
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          transaction.instrument_entity_name
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          transaction.transaction_type_name
            .toLowerCase()
            .includes(searchTerm.toLowerCase())
      );
    }

    if (selectedTransactionType) {
      processedData = processedData.filter(
        (transaction) =>
          transaction.transaction_type_id === selectedTransactionType
      );
    }

    if (selectedTransactionStatus) {
      processedData = processedData.filter(
        (transaction) =>
          transaction.transaction_status_id === selectedTransactionStatus
      );
    }

    return processedData;
  }, [
    rawTransactionsData,
    entities,
    transactionTypes,
    transactionStatuses,
    searchTerm,
    selectedTransactionType,
    selectedTransactionStatus,
  ]);

  const handleEdit = (transaction: apiService.Transaction) => {
    setEditingTransaction(transaction);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingTransaction(undefined);
  };

  const handleFormSuccess = () => {
    handleCloseForm();
    refetch();
  };

  const formatProperties = (properties: any) => {
    if (!properties) return "None";

    let parsedProperties;

    if (typeof properties === "string") {
      try {
        parsedProperties = JSON.parse(properties);
      } catch {
        return `Invalid JSON: ${properties.substring(0, 50)}...`;
      }
    } else if (typeof properties === "object") {
      parsedProperties = properties;
    } else {
      return String(properties);
    }

    try {
      const entries = Object.entries(parsedProperties);
      if (entries.length === 0) return "None";

      return entries
        .map(([key, value]) => {
          let valueType: string = typeof value;
          let displayValue = String(value);

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
      return "Invalid properties";
    }
  };

  const columns: GridColDef[] = [
    {
      field: "transaction_id",
      headerName: "ID",
      width: 80,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" fontWeight="bold">
          {params.value}
        </Typography>
      ),
    },
    {
      field: "portfolio_entity_name",
      headerName: "Portfolio",
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">{params.value}</Typography>
      ),
    },
    {
      field: "counterparty_entity_name",
      headerName: "Counterparty",
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">{params.value}</Typography>
      ),
    },
    {
      field: "instrument_entity_name",
      headerName: "Instrument",
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">{params.value}</Typography>
      ),
    },
    {
      field: "transaction_type_name",
      headerName: "Type",
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          color="primary"
          variant="outlined"
        />
      ),
    },
    {
      field: "transaction_status_name",
      headerName: "Status",
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          color="secondary"
          variant="outlined"
        />
      ),
    },
    {
      field: "properties",
      headerName: "Properties",
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
          {formatProperties(params.value)}
        </Typography>
      ),
    },
  ];

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={2}>
        <Typography color="error">
          Error loading transactions:{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </Typography>
        <Button onClick={() => refetch()} sx={{ mt: 1 }}>
          Retry
        </Button>
      </Box>
    );
  }

  const primaryClientGroupName =
    primaryClientGroup?.name || "this client group";

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <Typography variant="h5">Transactions</Typography>
        <Tooltip
          title="Transactions represent trades, transfers, or other financial activities between entities. Each transaction involves a party (buyer/seller), counterparty (other party), instrument (what was traded), and currency (denomination)."
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
          onClick={() => setIsFormOpen(true)}
          sx={{
            borderRadius: "20px",
            textTransform: "none",
            fontWeight: 600,
          }}
        >
          New
        </Button>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.5,
            marginLeft: "auto",
          }}
        >
          <Button
            variant="contained"
            color="primary"
            size="small"
            onClick={() => setIsTransactionTypesModalOpen(true)}
            sx={{
              borderRadius: "20px",
              textTransform: "none",
              fontWeight: 600,
            }}
          >
            Trans Types
          </Button>
          <Tooltip
            title="Manage transaction types and their properties. Transaction types define categories for organizing your transactions (e.g., Buy, Sell, Transfer)."
            placement="top"
          >
            <IconButton
              size="small"
              sx={{
                color: "primary.main",
                p: 0.25,
                "&:hover": {
                  backgroundColor: "rgba(25, 118, 210, 0.1)",
                },
              }}
            >
              <InfoOutlined fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, ml: 1 }}>
          <Button
            variant="contained"
            color="primary"
            size="small"
            onClick={() => setIsTransactionStatusesModalOpen(true)}
            sx={{
              borderRadius: "20px",
              textTransform: "none",
              fontWeight: 600,
            }}
          >
            Trans Status
          </Button>
          <Tooltip
            title="Manage transaction statuses. Transaction statuses track the state of transactions (e.g., Pending, Completed, Cancelled)."
            placement="top"
          >
            <IconButton
              size="small"
              sx={{
                color: "primary.main",
                p: 0.25,
                "&:hover": {
                  backgroundColor: "rgba(25, 118, 210, 0.1)",
                },
              }}
            >
              <InfoOutlined fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Filters */}
      <Box sx={{ mb: 2, display: "flex", gap: 2, flexWrap: "wrap" }}>
        <TextField
          label="Search transactions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        />
        <Autocomplete
          size="small"
          options={transactionTypes || []}
          getOptionLabel={(option) => option.name}
          value={
            transactionTypes?.find(
              (t) => t.transaction_type_id === selectedTransactionType
            ) || null
          }
          onChange={(_, newValue) =>
            setSelectedTransactionType(newValue?.transaction_type_id || null)
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label="Transaction Type"
              sx={{ minWidth: 150 }}
            />
          )}
          sx={{ minWidth: 200 }}
        />
        <Autocomplete
          size="small"
          options={transactionStatuses || []}
          getOptionLabel={(option) => option.name}
          value={
            transactionStatuses?.find(
              (s) => s.transaction_status_id === selectedTransactionStatus
            ) || null
          }
          onChange={(_, newValue) =>
            setSelectedTransactionStatus(
              newValue?.transaction_status_id || null
            )
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label="Transaction Status"
              sx={{ minWidth: 150 }}
            />
          )}
          sx={{ minWidth: 200 }}
        />
      </Box>

      {/* Data Grid */}
      <Box>
        <DataGrid
          rows={transactionsData}
          columns={columns}
          pageSizeOptions={[25, 50, 100]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 25 },
            },
          }}
          onRowClick={(params: GridRowParams) =>
            handleEdit(params.row as apiService.Transaction)
          }
          sx={{
            "& .MuiDataGrid-columnHeaders": {
              backgroundColor: "#f5f5f5 !important",
              borderBottom: "1px solid rgba(25, 118, 210, 0.2) !important",
            },
            "& .MuiDataGrid-columnHeader": {
              backgroundColor: "#f5f5f5 !important",
              display: "flex",
              alignItems: "center",
            },
          }}
          slots={{
            noRowsOverlay: () => (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  p: 3,
                }}
              >
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No transactions found
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  textAlign="center"
                >
                  No transactions exist for {primaryClientGroupName}
                  <br />
                  Click "New Transaction" to create one for{" "}
                  {primaryClientGroupName}.
                </Typography>
              </Box>
            ),
          }}
        />
      </Box>

      {/* Transaction Form Modal */}
      <Modal open={isFormOpen} onClose={handleCloseForm}>
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "90%",
            maxWidth: "800px",
            maxHeight: "90vh",
            overflow: "auto",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          <DynamicTransactionForm
            editingTransaction={editingTransaction}
            onClose={handleCloseForm}
          />
        </Box>
      </Modal>

      {/* Transaction Types Modal */}
      <Modal
        open={isTransactionTypesModalOpen}
        onClose={() => setIsTransactionTypesModalOpen(false)}
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "95%",
            maxWidth: "1200px",
            maxHeight: "90vh",
            overflow: "auto",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          <TransactionTypesTable />
        </Box>
      </Modal>

      {/* Transaction Statuses Modal */}
      <Modal
        open={isTransactionStatusesModalOpen}
        onClose={() => setIsTransactionStatusesModalOpen(false)}
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "95%",
            maxWidth: "1200px",
            maxHeight: "90vh",
            overflow: "auto",
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 24,
            p: 0,
          }}
        >
          <TransactionStatusesTable />
        </Box>
      </Modal>
    </Box>
  );
};

export default TransactionsTable;
