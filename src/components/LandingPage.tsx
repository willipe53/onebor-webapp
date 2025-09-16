import React, { useState } from 'react';
import {
  Box,
  Button,
  AppBar,
  Toolbar,
  Container,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import LoginDialog from './LoginDialog';
import SignupDialog from './SignupDialog';

const LogoContainer = styled(Box)({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '80vh',
});

const PlaceholderLogo = styled(Box)(({ theme }) => ({
  width: 200,
  height: 200,
  backgroundColor: '#1976d2',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
}));

const LandingPage: React.FC = () => {
  const [loginOpen, setLoginOpen] = useState(false);
  const [signupOpen, setSignupOpen] = useState(false);

  return (
    <Box>
      {/* Header with Login/Signup buttons */}
      <AppBar position="static" color="transparent" elevation={0}>
        <Toolbar sx={{ justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            sx={{ mr: 2 }}
            onClick={() => setLoginOpen(true)}
          >
            Client Login
          </Button>
          <Button
            variant="contained"
            onClick={() => setSignupOpen(true)}
          >
            Sign Up
          </Button>
        </Toolbar>
      </AppBar>

      {/* Main content with centered logo */}
      <Container maxWidth="md">
        <LogoContainer>
          <PlaceholderLogo>
            <Typography variant="h3" color="white" fontWeight="bold">
              LOGO
            </Typography>
          </PlaceholderLogo>
          <Typography variant="h4" color="text.primary" textAlign="center">
            Welcome to OneBor
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" textAlign="center" sx={{ mt: 1 }}>
            Your business solution platform
          </Typography>
        </LogoContainer>
      </Container>

      {/* Login Dialog */}
      <LoginDialog
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
      />

      {/* Signup Dialog */}
      <SignupDialog
        open={signupOpen}
        onClose={() => setSignupOpen(false)}
      />
    </Box>
  );
};

export default LandingPage;
