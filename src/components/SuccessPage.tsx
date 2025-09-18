import React, { useState } from "react";
import {
  Box,
  Typography,
  Button,
  AppBar,
  Toolbar,
  Container,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
} from "@mui/material";
import { CheckCircle, Add, ViewList, PersonAdd } from "@mui/icons-material";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../contexts/AuthContext";
import { styled } from "@mui/material/styles";
import oneborLogo from "../assets/images/oneborlogo.png";
import EntityForm from "./EntityForm";
import EntityTypeForm from "./EntityTypeForm";
import EntitiesTable from "./EntitiesTable";
import EntityTypesTable from "./EntityTypesTable";
import ClientGroupOnboarding from "./ClientGroupOnboarding";
import { InviteUserForm } from "./InviteUserForm";
import { useClientGroupOnboarding } from "../hooks/useClientGroupOnboarding";
import * as apiService from "../services/api";

const HeaderLogo = styled("img")({
  height: "40px",
  width: "auto",
});

const SuccessPage: React.FC = () => {
  const { userEmail, userName, userId, logout } = useAuth();
  const [currentTab, setCurrentTab] = useState(0);
  const [inviteUserOpen, setInviteUserOpen] = useState(false);

  // Client group onboarding logic
  const {
    isLoading: onboardingLoading,
    needsOnboarding,
    user,
    completeOnboarding,
  } = useClientGroupOnboarding(userEmail, userName, userId);

  // Query to get client group information
  const { data: clientGroups } = useQuery({
    queryKey: ["client-groups", user?.primary_client_group_id],
    queryFn: () => {
      if (!user?.primary_client_group_id) return Promise.resolve([]);
      return apiService.queryClientGroups({
        client_group_id: user.primary_client_group_id,
      });
    },
    enabled: !!user?.primary_client_group_id,
  });

  const primaryClientGroup =
    clientGroups && clientGroups.length > 0 ? clientGroups[0] : null;

  const handleOnboardingComplete = async (clientGroupId: number) => {
    try {
      await completeOnboarding(clientGroupId);
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
    }
  };

  const handleOnboardingCancel = () => {
    logout();
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const renderTabContent = () => {
    switch (currentTab) {
      case 0:
        return (
          <Container maxWidth="md">
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "60vh",
              }}
            >
              <Paper
                elevation={3}
                sx={{
                  p: 6,
                  textAlign: "center",
                  borderRadius: 2,
                  maxWidth: 500,
                }}
              >
                <CheckCircle
                  sx={{
                    fontSize: 80,
                    color: "success.main",
                    mb: 3,
                  }}
                />
                <Typography variant="h3" color="primary" gutterBottom>
                  Welcome to OneBor!
                </Typography>
                <Typography variant="h6" color="text.secondary" sx={{ mt: 2 }}>
                  You're successfully logged in as:
                </Typography>
                <Typography
                  variant="h5"
                  color="text.primary"
                  sx={{
                    mt: 2,
                    p: 2,
                    backgroundColor: "grey.100",
                    borderRadius: 1,
                    fontFamily: "monospace",
                  }}
                >
                  {userEmail}
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mt: 3 }}
                >
                  Use the tabs above to manage entities and entity types.
                </Typography>
              </Paper>
            </Box>
          </Container>
        );
      case 1:
        return <EntityForm />;
      case 2:
        return <EntityTypeForm />;
      case 3:
        return <EntitiesTable />;
      case 4:
        return <EntityTypesTable />;
      default:
        return null;
    }
  };

  // Show loading screen while checking user status
  if (onboardingLoading) {
    return (
      <Box>
        {/* Header with Logout button */}
        <AppBar position="static" color="primary">
          <Toolbar sx={{ justifyContent: "space-between" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <HeaderLogo src={oneborLogo} alt="OneBor Logo" />
              {primaryClientGroup && (
                <Typography
                  variant="h6"
                  component="div"
                  sx={{
                    color: "inherit",
                    fontWeight: 500,
                    display: { xs: "none", sm: "block" },
                  }}
                >
                  {primaryClientGroup.name}
                </Typography>
              )}
            </Box>
            <Button color="inherit" onClick={logout}>
              Logout
            </Button>
          </Toolbar>
        </AppBar>

        {/* Loading screen */}
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "calc(100vh - 64px)",
            gap: 2,
          }}
        >
          <CircularProgress size={40} />
          <Typography variant="body1" color="text.secondary">
            Setting up your account...
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with Logout button */}
      <AppBar position="static" color="primary">
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <HeaderLogo src={oneborLogo} alt="OneBor Logo" />
            {primaryClientGroup && (
              <Typography
                variant="h6"
                component="div"
                sx={{
                  color: "inherit",
                  fontWeight: 500,
                  display: { xs: "none", sm: "block" },
                }}
              >
                {primaryClientGroup.name}
              </Typography>
            )}
          </Box>
          <Button color="inherit" onClick={logout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Tabs value={currentTab} onChange={handleTabChange}>
            <Tab label="Dashboard" />
            <Tab icon={<Add />} label="New Entity" />
            <Tab icon={<Add />} label="New Entity Type" />
            <Tab icon={<ViewList />} label="Entities" />
            <Tab icon={<ViewList />} label="Entity Types" />
          </Tabs>
          <Box sx={{ pr: 2 }}>
            <Button
              variant="outlined"
              startIcon={<PersonAdd />}
              onClick={() => setInviteUserOpen(true)}
              sx={{ display: { xs: "none", sm: "flex" } }}
            >
              Invite User
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Tab Content */}
      <Box sx={{ minHeight: "calc(100vh - 120px)" }}>{renderTabContent()}</Box>

      {/* Client Group Onboarding Modal */}
      <ClientGroupOnboarding
        open={needsOnboarding}
        userEmail={userEmail || ""}
        userId={userId || ""}
        onComplete={handleOnboardingComplete}
        onCancel={handleOnboardingCancel}
      />

      {/* Invite User Modal */}
      <InviteUserForm
        open={inviteUserOpen}
        onClose={() => setInviteUserOpen(false)}
      />
    </Box>
  );
};

export default SuccessPage;
