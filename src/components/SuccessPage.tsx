import React from "react";
import {
  Box,
  Typography,
  Button,
  AppBar,
  Toolbar,
  Container,
  Paper,
} from "@mui/material";
import { CheckCircle } from "@mui/icons-material";
import { useAuth } from "../contexts/AuthContext";
import { styled } from "@mui/material/styles";
import oneborLogo from "../assets/images/oneborlogo.png";

const HeaderLogo = styled("img")({
  height: "40px",
  width: "auto",
  filter: "brightness(0) invert(1)", // Makes the logo white
});

const SuccessPage: React.FC = () => {
  const { userEmail, logout } = useAuth();

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

      {/* Main content */}
      <Container maxWidth="md">
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "80vh",
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
              Ok you are in!!!
            </Typography>
            <Typography variant="h6" color="text.secondary" sx={{ mt: 2 }}>
              Welcome, you're successfully logged in with:
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
            <Typography variant="body1" color="text.secondary" sx={{ mt: 3 }}>
              You now have access to the OneBor platform!
            </Typography>
          </Paper>
        </Box>
      </Container>
    </Box>
  );
};

export default SuccessPage;
