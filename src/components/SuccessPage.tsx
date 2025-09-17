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
} from "@mui/material";
import { CheckCircle, Add, ViewList } from "@mui/icons-material";
import { useAuth } from "../contexts/AuthContext";
import { styled } from "@mui/material/styles";
import oneborLogo from "../assets/images/oneborlogo.png";
import CreateEntityForm from "./CreateEntityForm";
import CreateEntityTypeForm from "./CreateEntityTypeForm";
import EntitiesTable from "./EntitiesTable";
import EntityTypesTable from "./EntityTypesTable";

const HeaderLogo = styled("img")({
  height: "40px",
  width: "auto",
  filter: "brightness(0) invert(1)", // Makes the logo white
});

const SuccessPage: React.FC = () => {
  const { userEmail, logout } = useAuth();
  const [currentTab, setCurrentTab] = useState(0);

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
        return <CreateEntityForm />;
      case 2:
        return <CreateEntityTypeForm />;
      case 3:
        return <EntitiesTable />;
      case 4:
        return <EntityTypesTable />;
      default:
        return null;
    }
  };

  return (
    <Box>
      {/* Header with Logout button */}
      <AppBar position="static" color="primary">
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <HeaderLogo src={oneborLogo} alt="OneBor Logo" />
          <Button color="inherit" onClick={logout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={currentTab} onChange={handleTabChange} centered>
          <Tab label="Dashboard" />
          <Tab icon={<Add />} label="New Entity" />
          <Tab icon={<Add />} label="New Entity Type" />
          <Tab icon={<ViewList />} label="Entities" />
          <Tab icon={<ViewList />} label="Entity Types" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ minHeight: "calc(100vh - 120px)" }}>{renderTabContent()}</Box>
    </Box>
  );
};

export default SuccessPage;
