import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import * as apiService from "../services/api";

interface ClientGroupOnboardingProps {
  open: boolean;
  userEmail: string;
  userId: string;
  onComplete: (clientGroupId: number) => void;
  onCancel: () => void;
}

const ClientGroupOnboarding: React.FC<ClientGroupOnboardingProps> = ({
  open,
  userEmail,
  userId,
  onComplete,
  onCancel,
}) => {
  const [step, setStep] = useState<
    "prompt" | "invitation-code" | "create-group" | "error"
  >("prompt");
  const [organizationName, setOrganizationName] = useState("");
  const [invitationCode, setInvitationCode] = useState("");
  const [error, setError] = useState<string>("");

  // Query to get user's current client groups
  const { data: userClientGroups } = useQuery({
    queryKey: ["user-client-groups", userId],
    queryFn: () => apiService.queryClientGroups({ user_id: userId }),
    enabled: !!userId,
  });

  const createClientGroupMutation = useMutation({
    mutationFn: (data: apiService.CreateClientGroupRequest) =>
      apiService.updateClientGroup(data),
    onSuccess: (result) => {
      onComplete(result.id);
    },
    onError: (error: Error) => {
      setError(
        error.message ||
          "Failed to create client organization. Please try again."
      );
      setStep("error");
    },
  });

  const validateInvitationMutation = useMutation({
    mutationFn: () =>
      apiService.manageInvitation({ action: "get", email: userEmail }),
    onSuccess: (invitations) => {
      const invitation = Array.isArray(invitations)
        ? invitations.find(
            (inv: apiService.Invitation) =>
              inv.code === invitationCode && !inv.redeemed
          )
        : null;

      if (!invitation) {
        setError("Invalid or expired invitation code");
        return;
      }

      // Check if invitation is expired
      const now = new Date();
      const expiresAt = new Date(invitation.expires_at);
      if (now > expiresAt) {
        setError("This invitation has expired");
        return;
      }

      // Proceed with redemption
      redeemInvitationMutation.mutate(invitation);
    },
    onError: () => {
      setError("Failed to validate invitation code. Please try again.");
    },
  });

  const redeemInvitationMutation = useMutation({
    mutationFn: async (invitation: apiService.Invitation) => {
      // Add user to client group
      await apiService.modifyClientGroupMembership({
        client_group_id: invitation.primary_client_group_id,
        user_id: userId,
        add_or_remove: "add",
      });

      // If this is their only client group, set it as primary
      const currentGroups = userClientGroups || [];
      if (currentGroups.length === 0) {
        await apiService.updateUser({
          user_id: userId,
          primary_client_group_id: invitation.primary_client_group_id,
        });
      }

      // Mark invitation as redeemed
      await apiService.manageInvitation({
        action: "redeem",
        code: invitation.code,
      });

      return invitation.primary_client_group_id;
    },
    onSuccess: (clientGroupId) => {
      onComplete(clientGroupId);
    },
    onError: () => {
      setError("Failed to redeem invitation. Please try again.");
    },
  });

  const handleCreateOrganization = () => {
    if (!organizationName.trim()) {
      setError("Organization name is required");
      return;
    }

    createClientGroupMutation.mutate({
      name: organizationName.trim(),
    });
  };

  const handleValidateInvitation = () => {
    if (!invitationCode.trim()) {
      setError("Invitation code is required");
      return;
    }

    setError("");
    validateInvitationMutation.mutate();
  };

  const handleCancel = () => {
    setStep("error");
  };

  const handleTryAgain = () => {
    setStep("prompt");
    setError("");
    setOrganizationName("");
    setInvitationCode("");
  };

  return (
    <Dialog
      open={open}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown
      PaperProps={{
        sx: { borderRadius: 2 },
      }}
    >
      {step === "prompt" && (
        <>
          <DialogTitle sx={{ pb: 2 }}>
            <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
              Client Organization Required
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.6 }}>
              I was unable to associate your email address{" "}
              <strong>({userEmail})</strong> with a client organization.
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.6 }}>
              Please choose one of the following options:
            </Typography>
            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 2 }}
            >
              <Button
                onClick={() => setStep("invitation-code")}
                variant="outlined"
                fullWidth
                sx={{ justifyContent: "flex-start", textAlign: "left" }}
              >
                I have an invitation code from my administrator
              </Button>
              <Button
                onClick={() => setStep("create-group")}
                variant="outlined"
                fullWidth
                sx={{ justifyContent: "flex-start", textAlign: "left" }}
              >
                Create a new client organization
              </Button>
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={handleCancel}
              variant="outlined"
              color="error"
              sx={{ mr: 1 }}
            >
              Cancel
            </Button>
          </DialogActions>
        </>
      )}

      {step === "create-group" && (
        <>
          <DialogTitle sx={{ pb: 2 }}>
            <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
              Create Client Organization
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.6 }}>
              Please provide a name for your client organization:
            </Typography>
            <TextField
              fullWidth
              label="Organization Name"
              placeholder="e.g., Acme Corporation, Smith & Associates"
              value={organizationName}
              onChange={(e) => setOrganizationName(e.target.value)}
              disabled={createClientGroupMutation.isPending}
              autoFocus
              sx={{ mb: 2 }}
              helperText="This will be used to identify your organization in OneBor"
            />
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setStep("prompt")}
              variant="outlined"
              disabled={createClientGroupMutation.isPending}
              sx={{ mr: 1 }}
            >
              Back
            </Button>
            <Button
              onClick={handleCreateOrganization}
              variant="contained"
              color="primary"
              disabled={
                !organizationName.trim() || createClientGroupMutation.isPending
              }
              startIcon={
                createClientGroupMutation.isPending ? (
                  <CircularProgress size={20} />
                ) : null
              }
            >
              {createClientGroupMutation.isPending
                ? "Creating..."
                : "Create Organization"}
            </Button>
          </DialogActions>
        </>
      )}

      {step === "invitation-code" && (
        <>
          <DialogTitle sx={{ pb: 2 }}>
            <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
              Enter Invitation Code
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.6 }}>
              Please enter the invitation code you received from your
              administrator:
            </Typography>
            <TextField
              fullWidth
              label="Invitation Code"
              placeholder="Enter your invitation code here"
              value={invitationCode}
              onChange={(e) => setInvitationCode(e.target.value)}
              disabled={
                validateInvitationMutation.isPending ||
                redeemInvitationMutation.isPending
              }
              autoFocus
              sx={{ mb: 2 }}
              helperText="The code should have been sent to you via email"
            />
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              onClick={() => setStep("prompt")}
              variant="outlined"
              disabled={
                validateInvitationMutation.isPending ||
                redeemInvitationMutation.isPending
              }
              sx={{ mr: 1 }}
            >
              Back
            </Button>
            <Button
              onClick={handleValidateInvitation}
              variant="contained"
              color="primary"
              disabled={
                !invitationCode.trim() ||
                validateInvitationMutation.isPending ||
                redeemInvitationMutation.isPending
              }
              startIcon={
                validateInvitationMutation.isPending ||
                redeemInvitationMutation.isPending ? (
                  <CircularProgress size={20} />
                ) : null
              }
            >
              {validateInvitationMutation.isPending ||
              redeemInvitationMutation.isPending
                ? "Processing..."
                : "Validate Code"}
            </Button>
          </DialogActions>
        </>
      )}

      {step === "error" && (
        <>
          <DialogTitle sx={{ pb: 2 }}>
            <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
              Access Denied
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Alert severity="error" sx={{ mb: 3 }}>
              <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
                We are sorry we cannot give you access to OneBor without
                assigning you to a client organization.
              </Typography>
            </Alert>
            <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
              Please contact the person at your firm who administers OneBor for
              further instructions.
            </Typography>
            {error && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="body2">{error}</Typography>
              </Alert>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            {error && (
              <Button
                onClick={handleTryAgain}
                variant="outlined"
                color="primary"
                sx={{ mr: 1 }}
              >
                Try Again
              </Button>
            )}
            <Button onClick={onCancel} variant="contained" color="error">
              Sign Out
            </Button>
          </DialogActions>
        </>
      )}
    </Dialog>
  );
};

export default ClientGroupOnboarding;
