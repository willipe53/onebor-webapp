import React, { useState } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Button,
  Chip,
  Tooltip,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import { parseServerDate, formatLocalDateShort } from "../utils";
import { Add, InfoOutlined } from "@mui/icons-material";
import { InviteUserForm } from "./InviteUserForm";
import * as apiService from "../services/api";

const InvitationsTable: React.FC = () => {
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const [inviteUserOpen, setInviteUserOpen] = useState(false);
  const [filter, setFilter] = useState<"unexpired" | "all">("unexpired");

  // Get current user's database ID
  const { data: currentUser } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => apiService.queryUsers({ sub: userId! }),
    enabled: !!userId,
    select: (data) => data[0], // Get first user from array
  });

  // console.log("🔍 InvitationsTable - Current user:", currentUser);
  // console.log(
  //   "🔍 InvitationsTable - Primary client group ID:",
  //   currentUser?.primary_client_group_id
  // );

  // Get all client groups the user belongs to for debugging
  const { data: userClientGroups } = useQuery({
    queryKey: ["client-groups", currentUser?.user_id],
    queryFn: () =>
      apiService.queryClientGroups({ user_id: currentUser!.user_id }),
    enabled: !!currentUser?.user_id,
  });

  // console.log("🔍 InvitationsTable - User's client groups:", userClientGroups);

  // Get primary client group details (including name)
  const { data: primaryClientGroup } = useQuery({
    queryKey: ["primary-client-group", currentUser?.primary_client_group_id],
    queryFn: () =>
      apiService.queryClientGroups({
        client_group_id: currentUser!.primary_client_group_id!,
      }),
    enabled: !!currentUser?.primary_client_group_id,
    select: (data) => data[0], // Get first group from array
  });

  // Debug: Try fetching invitations for ALL the user's client groups
  const { data: debugInvitations } = useQuery({
    queryKey: ["debug-all-invitations", userClientGroups],
    queryFn: async () => {
      if (!userClientGroups || userClientGroups.length === 0) return [];

      const allInvitations = [];
      for (const group of userClientGroups) {
        try {
          // console.log(
          //   `🔍 Fetching invitations for group ${group.client_group_id} (${group.name})`
          // );
          const invitations = await apiService.manageInvitation({
            action: "get",
            client_group_id: group.client_group_id,
          });
          // console.log(
          //   `🔍 Group ${group.client_group_id} invitations:`,
          //   invitations
          // );

          if (Array.isArray(invitations)) {
            allInvitations.push(
              ...invitations.map((inv) => ({ ...inv, group_name: group.name }))
            );
          } else if (invitations) {
            allInvitations.push({ ...invitations, group_name: group.name });
          }
        } catch (error) {
          console.error(
            `Error fetching invitations for group ${group.client_group_id}:`,
            error
          );
        }
      }
      return allInvitations;
    },
    enabled: !!userClientGroups && userClientGroups.length > 0,
  });

  // console.log(
  //   "🔍 InvitationsTable - All invitations across all groups:",
  //   debugInvitations
  // );

  // Fetch invitations for the user's client group
  const {
    data: rawInvitationsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["invitations", currentUser?.primary_client_group_id],
    queryFn: () => {
      // console.log(
      //   "🔍 InvitationsTable - Fetching invitations for client_group_id:",
      //   currentUser!.primary_client_group_id
      // );
      return apiService.manageInvitation({
        action: "get",
        client_group_id: currentUser!.primary_client_group_id!,
      });
    },
    enabled: !!currentUser?.primary_client_group_id,
  });

  // console.log(
  //   "🔍 InvitationsTable - Raw invitations data:",
  //   rawInvitationsData
  // );
  // console.log("🔍 InvitationsTable - Is loading:", isLoading);
  // console.log("🔍 InvitationsTable - Error:", error);

  // Mutation to expire an invitation
  const expireInvitationMutation = useMutation({
    mutationFn: (code: string) => {
      // console.log("🔄 Calling manageInvitation with:", {
      //   action: "redeem",
      //   code,
      // });
      return apiService.manageInvitation({
        action: "redeem", // This sets expires_at to NOW()
        code,
      });
    },
    onSuccess: () => {
      // console.log("✅ Invitation expired successfully, refreshing table...");
      // Refresh the invitations list
      refetch();
      // Invalidate the count cache to update badges
      queryClient.invalidateQueries({ queryKey: ["invitation-count"] });
      queryClient.invalidateQueries({ queryKey: ["invitation-count-all"] });
      queryClient.invalidateQueries({
        queryKey: ["invitation-count-unexpired"],
      });
    },
    onError: (error) => {
      console.error("Failed to expire invitation:", error);
    },
  });

  // Transform array data to proper format
  const invitationsData = React.useMemo(() => {
    // console.log(
    //   "🔍 InvitationsTable - Processing raw data:",
    //   rawInvitationsData
    // );
    // console.log(
    //   "🔍 InvitationsTable - Processing debug data:",
    //   debugInvitations
    // );

    // For now, use debugInvitations (all groups) if rawInvitationsData is empty
    const sourceData =
      rawInvitationsData &&
      Array.isArray(rawInvitationsData) &&
      rawInvitationsData.length > 0
        ? rawInvitationsData
        : debugInvitations || [];

    if (!sourceData || (Array.isArray(sourceData) && sourceData.length === 0)) {
      // console.log(
      //   "🔍 InvitationsTable - No source data, returning empty array"
      // );
      return [];
    }

    // Handle both array and object responses
    const dataArray = Array.isArray(sourceData) ? sourceData : [sourceData];

    // console.log("🔍 InvitationsTable - Data array:", dataArray);
    // console.log("🔍 InvitationsTable - Data array length:", dataArray.length);

    const processed = dataArray.map((invitation: any) => {
      // Parse server date (UTC) and compare with current time
      const expiresAt = parseServerDate(invitation.expires_at);
      const now = new Date();
      const isExpired = expiresAt < now;

      // Find the group name if not already included
      const groupName =
        invitation.group_name ||
        userClientGroups?.find(
          (group) => group.client_group_id === invitation.client_group_id
        )?.name ||
        "Unknown";

      // Debug logging (remove in production)
      // console.log(
      //   `📅 Invitation ${invitation.code}: expires_at=${
      //     invitation.expires_at
      //   } (server UTC), local=${formatLocalDateShort(
      //     expiresAt
      //   )}, isExpired=${isExpired}, group=${groupName}`
      // );

      return {
        id: invitation.invitation_id,
        invitation_id: invitation.invitation_id,
        code: invitation.code,
        expires_at: invitation.expires_at,
        expires_at_local: formatLocalDateShort(expiresAt), // Store formatted local time for display
        client_group_id: invitation.client_group_id,
        group_name: groupName,
        isExpired: isExpired,
      };
    });

    // console.log("🔍 InvitationsTable - Processed invitations data:", processed);
    // console.log(
    //   "🔍 InvitationsTable - Processed data length:",
    //   processed.length
    // );

    // Apply filter based on the toggle
    const filteredProcessed =
      filter === "unexpired"
        ? processed.filter((invitation) => !invitation.isExpired)
        : processed;

    return filteredProcessed;
  }, [rawInvitationsData, debugInvitations, userClientGroups, filter]);

  const handleExpireInvitation = (code: string) => {
    expireInvitationMutation.mutate(code);
  };

  const columns: GridColDef[] = [
    {
      field: "invitation_id",
      headerName: "ID",
      width: 80,
      type: "number",
      align: "left",
      headerAlign: "left",
    },
    {
      field: "code",
      headerName: "Invitation Code",
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" fontFamily="monospace">
          {params.value}
        </Typography>
      ),
    },
    {
      field: "group_name",
      headerName: "Client Group",
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">{params.value || "Unknown"}</Typography>
      ),
    },
    {
      field: "expires_at_local",
      headerName: "Expires At",
      width: 220,
      renderCell: (params: GridRenderCellParams) => {
        const isExpired = params.row.isExpired;

        return (
          <Chip
            label={params.value} // Already formatted in local time
            color={isExpired ? "error" : "success"}
            variant="outlined"
            size="small"
          />
        );
      },
    },
    {
      field: "actions",
      headerName: "Expire Code",
      flex: 1,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => {
        const isExpired = params.row.isExpired;
        const isExpiring = expireInvitationMutation.isPending;

        return (
          <Button
            variant="outlined"
            color="error"
            size="small"
            onClick={() => handleExpireInvitation(params.row.code)}
            disabled={isExpired || isExpiring}
            sx={{ minWidth: "140px" }}
          >
            {isExpired ? "Already Expired" : "Expire Invitation"}
          </Button>
        );
      },
    },
  ];

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Typography color="error" variant="h6">
          Error loading invitations
        </Typography>
        <Typography color="error" variant="body2">
          {error instanceof Error ? error.message : "Unknown error occurred"}
        </Typography>
        <Button onClick={() => refetch()} variant="outlined" sx={{ mt: 2 }}>
          Try Again
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Typography variant="h5">Invitations</Typography>
        <Tooltip
          title="Invitations are the way that new users are set up in onebor. The user receives an email containing a code that will allow them to get access to your organization."
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
          onClick={() => setInviteUserOpen(true)}
          sx={{
            borderRadius: "20px",
            textTransform: "none",
            fontWeight: 600,
            ml: "auto",
          }}
        >
          New
        </Button>

        <ToggleButtonGroup
          value={filter}
          exclusive
          onChange={(_, newFilter) => {
            if (newFilter !== null) {
              setFilter(newFilter);
            }
          }}
          size="small"
          sx={{ ml: 1 }}
        >
          <ToggleButton value="unexpired">Unexpired</ToggleButton>
          <ToggleButton value="all">All</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Data Grid */}
      <Box sx={{ height: 600, width: "100%" }}>
        {invitationsData.length === 0 && !isLoading ? (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              {!currentUser?.primary_client_group_id ? (
                "User doesn't have a primary client group set"
              ) : (
                <>
                  No {filter === "unexpired" ? "unexpired " : ""}invitations
                  found
                  <br />
                  No {filter === "unexpired" ? "unexpired " : ""}invitations
                  exist for {primaryClientGroup?.name || "this client group"}
                  <br />
                  Click "New" to invite a user to join{" "}
                  {primaryClientGroup?.name || "this client group"} via email.
                </>
              )}
            </Typography>
          </Box>
        ) : (
          <DataGrid
            rows={invitationsData}
            columns={columns}
            pagination
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: {
                paginationModel: { pageSize: 10, page: 0 },
              },
            }}
            disableRowSelectionOnClick
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
        )}
      </Box>

      {/* Invite User Modal */}
      <InviteUserForm
        open={inviteUserOpen}
        onClose={() => {
          setInviteUserOpen(false);
          refetch(); // Refresh the invitations list
          // Invalidate the count cache to update badges
          queryClient.invalidateQueries({ queryKey: ["invitation-count"] });
          queryClient.invalidateQueries({ queryKey: ["invitation-count-all"] });
          queryClient.invalidateQueries({
            queryKey: ["invitation-count-unexpired"],
          });
        }}
      />
    </Box>
  );
};

export default InvitationsTable;
