import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Box,
  Typography,
  Chip,
  CircularProgress,
} from "@mui/material";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { useQuery, useMutation } from "@tanstack/react-query";
import * as apiService from "../services/api";
import type { ClientGroup, CreateInvitationRequest } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

interface InviteUserFormProps {
  open: boolean;
  onClose: () => void;
}

interface FormData {
  clientGroupId: number | "";
  email: string;
  name: string;
  expiresAt: Date | null;
}

interface ValidationError {
  field: string;
  message: string;
}

export const InviteUserForm: React.FC<InviteUserFormProps> = ({
  open,
  onClose,
}) => {
  const { userId } = useAuth();

  const [formData, setFormData] = useState<FormData>({
    clientGroupId: "",
    email: "",
    name: "",
    expiresAt: null,
  });

  const [validationErrors, setValidationErrors] = useState<ValidationError[]>(
    []
  );
  const [invitationCode, setInvitationCode] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch current user data to get primary client group
  const { data: currentUser } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ user_id: userId! }),
    enabled: !!userId,
    select: (data) => data[0], // Assuming queryUsers returns an array
  });

  // Fetch client groups for the dropdown
  const { data: clientGroups = [] } = useQuery<ClientGroup[]>({
    queryKey: ["clientGroups"],
    queryFn: () => apiService.queryClientGroups({}),
    enabled: open,
  });

  // Check if email is already a member of selected client group
  const { refetch: checkExistingUser } = useQuery({
    queryKey: ["existingUsers", formData.email, formData.clientGroupId],
    queryFn: () => apiService.queryUsers({ email: formData.email }),
    enabled: false, // Only run when manually triggered
    retry: false,
  });

  // Create invitation mutation
  const createInvitationMutation = useMutation({
    mutationFn: (data: CreateInvitationRequest) =>
      apiService.manageInvitation(data),
    onSuccess: (response) => {
      if (typeof response === "object" && "code" in response) {
        setInvitationCode(response.code);
        setIsGenerating(false);
      }
    },
    onError: (error) => {
      console.error("Failed to create invitation:", error);
      setIsGenerating(false);
    },
  });

  // Initialize form with default values
  useEffect(() => {
    if (open && currentUser && clientGroups.length > 0) {
      setFormData({
        clientGroupId: currentUser.primary_client_group_id || "",
        email: "",
        name: "",
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours from now
      });
      setValidationErrors([]);
      setInvitationCode("");
    }
  }, [open, currentUser, clientGroups]);

  // Validate email format
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Check if user is already a member of the selected client group
  const checkUserMembership = async () => {
    if (!formData.email || !formData.clientGroupId) return;

    try {
      const result = await checkExistingUser();
      if (result.data && result.data.length > 0) {
        const existingUser = result.data[0];
        if (existingUser.primary_client_group_id === formData.clientGroupId) {
          const clientGroup = clientGroups.find(
            (cg) => cg.client_group_id === formData.clientGroupId
          );
          setValidationErrors([
            {
              field: "email",
              message: `${formData.email} is already a member of ${
                clientGroup?.name || "this client group"
              }`,
            },
          ]);
          return false;
        }
      }
      return true;
    } catch (error) {
      console.error("Error checking user membership:", error);
      return true;
    }
  };

  // Validate form
  const validateForm = async (): Promise<boolean> => {
    const errors: ValidationError[] = [];

    if (!formData.clientGroupId) {
      errors.push({
        field: "clientGroupId",
        message: "Please select a client group",
      });
    }

    if (!formData.email) {
      errors.push({ field: "email", message: "Email is required" });
    } else if (!validateEmail(formData.email)) {
      errors.push({
        field: "email",
        message: "Please enter a valid email address",
      });
    }

    if (!formData.name.trim()) {
      errors.push({ field: "name", message: "Name is required" });
    }

    if (!formData.expiresAt) {
      errors.push({
        field: "expiresAt",
        message: "Expiration date is required",
      });
    } else if (formData.expiresAt <= new Date()) {
      errors.push({
        field: "expiresAt",
        message: "Expiration date must be in the future",
      });
    }

    setValidationErrors(errors);

    if (errors.length === 0) {
      // Check if user is already a member
      const isNotMember = await checkUserMembership();
      return isNotMember ?? true;
    }

    return false;
  };

  // Handle form submission
  const handleGenerateInvitation = async () => {
    const isValid = await validateForm();
    if (!isValid) return;

    setIsGenerating(true);

    createInvitationMutation.mutate({
      action: "create",
      email: formData.email,
      name: formData.name,
      expires_at: formData.expiresAt!.toISOString(),
      primary_client_group_id: formData.clientGroupId as number,
    });
  };

  // Handle send invitation
  const handleSendInvitation = () => {
    const selectedClientGroup = clientGroups.find(
      (cg) => cg.client_group_id === formData.clientGroupId
    );
    const expiresAtFormatted = formData.expiresAt!.toLocaleString();

    const subject = `Welcome to ${selectedClientGroup?.name}`;
    const body = `Welcome to ${selectedClientGroup?.name}

You have been granted an invitation to join a OneBor client group by one of your administrators. This invitation will expire at ${expiresAtFormatted}. Please click on the link below or copy the code in this email to accept the invitation.

Link to accept: <a href="onebor.com/accept_invitation/${invitationCode} />

Invitation code: ${invitationCode}

If you have any questions please contact the person at your firm who administers OneBor.`;

    const mailtoUrl = `mailto:${formData.email}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(body)}`;
    window.open(mailtoUrl);
  };

  // Handle close
  const handleClose = () => {
    setFormData({
      clientGroupId: "",
      email: "",
      name: "",
      expiresAt: null,
    });
    setValidationErrors([]);
    setInvitationCode("");
    setIsGenerating(false);
    onClose();
  };

  // Get error message for a field
  const getFieldError = (field: string): string | undefined => {
    return validationErrors.find((error) => error.field === field)?.message;
  };

  // Check if form is valid for generating invitation
  const canGenerateInvitation =
    !!formData.clientGroupId &&
    !!formData.email &&
    !!formData.name.trim() &&
    !!formData.expiresAt &&
    validationErrors.length === 0;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="h6">Invite User</Typography>
          {invitationCode && (
            <Chip
              label={`Code: ${invitationCode}`}
              color="primary"
              size="small"
            />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box display="flex" flexDirection="column" gap={2} sx={{ mt: 1 }}>
          {/* Client Group Selection */}
          <FormControl fullWidth error={!!getFieldError("clientGroupId")}>
            <InputLabel>Invite To Join</InputLabel>
            <Select
              value={formData.clientGroupId}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  clientGroupId: e.target.value as number,
                })
              }
              label="Invite To Join"
            >
              {clientGroups.map((group) => (
                <MenuItem
                  key={group.client_group_id}
                  value={group.client_group_id}
                >
                  {group.name}
                  {group.client_group_id ===
                    currentUser?.primary_client_group_id && " (Primary)"}
                </MenuItem>
              ))}
            </Select>
            {getFieldError("clientGroupId") && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                {getFieldError("clientGroupId")}
              </Typography>
            )}
          </FormControl>

          {/* Email Field */}
          <TextField
            fullWidth
            label="Invitee Email"
            value={formData.email}
            onChange={(e) =>
              setFormData({ ...formData, email: e.target.value })
            }
            error={!!getFieldError("email")}
            helperText={getFieldError("email")}
            type="email"
          />

          {/* Name Field */}
          <TextField
            fullWidth
            label="Invitee Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            error={!!getFieldError("name")}
            helperText={getFieldError("name")}
          />

          {/* Expiration Date */}
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DateTimePicker
              label="Invite Expires At"
              value={formData.expiresAt}
              onChange={(newValue) =>
                setFormData({ ...formData, expiresAt: newValue })
              }
              slotProps={{
                textField: {
                  fullWidth: true,
                  error: !!getFieldError("expiresAt"),
                  helperText: getFieldError("expiresAt"),
                },
              }}
            />
          </LocalizationProvider>

          {/* Invitation Code Display */}
          {invitationCode && (
            <Alert severity="success">
              <Typography variant="body2">
                Invitation generated successfully! Use the "Send Invitation"
                button to email the invitation.
              </Typography>
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>

        {!invitationCode ? (
          <Button
            variant="contained"
            onClick={handleGenerateInvitation}
            disabled={!canGenerateInvitation || isGenerating}
            startIcon={isGenerating ? <CircularProgress size={20} /> : null}
          >
            {isGenerating ? "Generating..." : "Generate Invitation"}
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleSendInvitation}
            color="success"
          >
            Send Invitation
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
