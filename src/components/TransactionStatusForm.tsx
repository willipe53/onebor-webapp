import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Snackbar,
  Chip,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as apiService from "../services/api";
import AuditTrail from "./AuditTrail";

interface TransactionStatus {
  transaction_status_id: number;
  name: string;
  update_date?: string;
  updated_user_id?: number;
}

interface TransactionStatusFormProps {
  editingTransactionStatus?: TransactionStatus;
  onClose?: () => void;
}

const TransactionStatusForm: React.FC<TransactionStatusFormProps> = ({
  editingTransactionStatus,
  onClose,
}) => {
  const [name, setName] = useState("");
  const [showSuccessSnackbar, setShowSuccessSnackbar] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [initialFormState, setInitialFormState] = useState<{
    name: string;
  } | null>(null);

  const queryClient = useQueryClient();

  // Function to check if form is dirty
  const checkIfDirty = useCallback(() => {
    if (!initialFormState) return false;

    const currentState = {
      name,
    };

    return currentState.name !== initialFormState.name;
  }, [name, initialFormState]);

  // Update dirty state whenever form values change
  useEffect(() => {
    setIsDirty(checkIfDirty());
  }, [checkIfDirty]);

  // Populate form when editing a transaction status
  useEffect(() => {
    if (editingTransactionStatus) {
      setName(editingTransactionStatus.name || "");

      // Set initial form state for dirty tracking
      setTimeout(() => {
        setInitialFormState({
          name: editingTransactionStatus.name || "",
        });
        setIsDirty(false); // Reset dirty state when loading existing transaction status
      }, 0);
    } else {
      // For new transaction statuses, set initial state immediately
      setInitialFormState({
        name: "",
      });
      setIsDirty(false);
    }
  }, [editingTransactionStatus]);

  const mutation = useMutation({
    mutationFn: editingTransactionStatus
      ? apiService.updateTransactionStatus
      : apiService.createTransactionStatus,
    onSuccess: () => {
      if (!editingTransactionStatus) {
        // Reset form only for create mode
        setName("");
      }
      // Show success notification
      setShowSuccessSnackbar(true);

      // Invalidate and refetch transaction statuses queries to refresh tables immediately
      queryClient.invalidateQueries({ queryKey: ["transaction-statuses"] });
      queryClient.refetchQueries({ queryKey: ["transaction-statuses"] });

      // Close modal after successful operation (with a small delay to show the success message)
      if (onClose) {
        setTimeout(() => {
          onClose();
        }, 1000); // 1 second delay to show success message
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const requestData: apiService.CreateTransactionStatusRequest & {
        transaction_status_id?: number;
      } = {
        name,
      };

      // Add transaction_status_id for updates
      if (editingTransactionStatus) {
        requestData.transaction_status_id =
          editingTransactionStatus.transaction_status_id;
      }
      mutation.mutate(requestData);
    } catch (error) {
      console.error("Error preparing request:", error);
    }
  };

  const canSubmit =
    name.trim() &&
    !mutation.isPending &&
    (editingTransactionStatus?.transaction_status_id ? isDirty : true); // For existing statuses, require dirty; for new statuses, always allow

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
            {editingTransactionStatus
              ? "Edit Transaction Status"
              : "Create Transaction Status"}
          </Typography>
          {editingTransactionStatus && (
            <Chip
              label={`ID: ${editingTransactionStatus.transaction_status_id}`}
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
                editingTransactionStatus ? "update" : "create"
              } transaction status`}
          </Alert>
        )}

        {mutation.isSuccess && !editingTransactionStatus && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Transaction status created successfully!
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 3,
              mb: 3,
            }}
          >
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
              disabled={mutation.isPending}
              placeholder="e.g., Pending, Processed, Failed, Cancelled"
            />

            {/* Audit Trail */}
            <AuditTrail
              updateDate={editingTransactionStatus?.update_date}
              updatedUserId={editingTransactionStatus?.updated_user_id}
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 2,
                mt: 2,
              }}
            >
              {editingTransactionStatus && onClose && (
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
                    {editingTransactionStatus ? "Updating..." : "Creating..."}
                  </>
                ) : editingTransactionStatus?.transaction_status_id ? (
                  `Update ${editingTransactionStatus.name}`
                ) : (
                  "Create Transaction Status"
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
          {editingTransactionStatus
            ? "Transaction status updated successfully!"
            : "Transaction status created successfully!"}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TransactionStatusForm;
