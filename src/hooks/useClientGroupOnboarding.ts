import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as apiService from "../services/api";

interface OnboardingState {
  isLoading: boolean;
  needsOnboarding: boolean;
  user: apiService.User | null;
  error: string | null;
}

export const useClientGroupOnboarding = (
  userEmail: string | null,
  userName: string | null,
  cognitoUserId: string | null
) => {
  const [state, setState] = useState<OnboardingState>({
    isLoading: true,
    needsOnboarding: false,
    user: null,
    error: null,
  });

  const queryClient = useQueryClient();
  const hasProcessedRef = useRef(false);
  const processingRef = useRef(false);
  const lastUserIdRef = useRef<string | null>(null);

  // Query to get user data
  const { data: users, refetch: refetchUser } = useQuery({
    queryKey: ["user", cognitoUserId],
    queryFn: () => {
      if (!cognitoUserId) return Promise.resolve([]);
      return apiService.queryUsers({ user_id: cognitoUserId });
    },
    enabled: !!cognitoUserId && !!userEmail,
  });

  // Mutation to create/update user
  const updateUserMutation = useMutation({
    mutationFn: (
      data: apiService.UpdateUserRequest | apiService.CreateUserRequest
    ) => apiService.updateUser(data),
    onSuccess: () => {
      refetchUser();
    },
  });

  // Mutation to update user's primary client group
  const assignClientGroupMutation = useMutation({
    mutationFn: ({
      userId,
      clientGroupId,
    }: {
      userId: string;
      clientGroupId: number;
    }) =>
      apiService.updateUser({
        user_id: userId,
        primary_client_group_id: clientGroupId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
      setState((prev) => ({ ...prev, needsOnboarding: false }));
    },
  });

  useEffect(() => {
    if (!cognitoUserId || !userEmail || !userName) {
      setState({
        isLoading: false,
        needsOnboarding: false,
        user: null,
        error: null,
      });
      hasProcessedRef.current = false;
      lastUserIdRef.current = null;
      return;
    }

    // Reset processing state if user changed
    if (lastUserIdRef.current !== cognitoUserId) {
      hasProcessedRef.current = false;
      processingRef.current = false;
      lastUserIdRef.current = cognitoUserId;
    }

    // Skip if we're already processing or have already processed this user
    if (processingRef.current || hasProcessedRef.current) {
      return;
    }

    // Skip if users data is not yet loaded
    if (users === undefined) {
      return;
    }

    const handleUserCheck = async () => {
      if (processingRef.current) return;

      try {
        processingRef.current = true;
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        // Check if user exists
        const existingUsers = users || [];
        let currentUser = existingUsers.find(
          (u) => u.user_id === cognitoUserId
        );

        if (currentUser) {
          // User exists - update email and name if needed
          if (
            currentUser.email !== userEmail ||
            currentUser.name !== userName
          ) {
            try {
              const updateResult = await updateUserMutation.mutateAsync({
                user_id: cognitoUserId,
                email: userEmail,
                name: userName,
              });
              // Invalidate cache and refetch to get updated data
              queryClient.invalidateQueries({
                queryKey: ["user", cognitoUserId],
              });
              const updatedUsers = await refetchUser();

              currentUser =
                updatedUsers.data?.find((u) => u.user_id === cognitoUserId) ||
                currentUser;
            } catch (userUpdateError) {
              console.error("Failed to update user:", userUpdateError);
              throw new Error(
                `Failed to update user: ${userUpdateError.message}`
              );
            }
          }
        } else {
          // User doesn't exist - create new user
          try {
            await updateUserMutation.mutateAsync({
              user_id: cognitoUserId,
              email: userEmail,
              name: userName,
            });

            // Invalidate cache and refetch to get the new user data
            queryClient.invalidateQueries({
              queryKey: ["user", cognitoUserId],
            });
            await new Promise((resolve) => setTimeout(resolve, 500));

            const updatedUsers = await refetchUser();
            currentUser = updatedUsers.data?.find(
              (u) => u.user_id === cognitoUserId
            );
          } catch (userCreationError) {
            console.error("Failed to create user:", userCreationError);
            throw new Error(
              `Failed to create user: ${userCreationError.message}`
            );
          }
        }

        if (!currentUser) {
          throw new Error("Failed to create or retrieve user record");
        }

        // Check if user needs client group assignment
        const needsOnboarding = !currentUser.primary_client_group_id;

        setState({
          isLoading: false,
          needsOnboarding,
          user: currentUser,
          error: null,
        });

        hasProcessedRef.current = true;
      } catch (error: any) {
        console.error("Client group onboarding error:", error);
        setState({
          isLoading: false,
          needsOnboarding: false,
          user: null,
          error: error.message || "Failed to check user status",
        });
        hasProcessedRef.current = true;
      } finally {
        processingRef.current = false;
      }
    };

    handleUserCheck();
  }, [cognitoUserId, userEmail, userName, users]);

  const completeOnboarding = async (clientGroupId: number) => {
    if (!cognitoUserId) {
      throw new Error("No user ID available");
    }

    await assignClientGroupMutation.mutateAsync({
      userId: cognitoUserId,
      clientGroupId,
    });

    // Reset processing state after successful onboarding
    hasProcessedRef.current = false;
  };

  return {
    ...state,
    completeOnboarding,
    isUpdating:
      updateUserMutation.isPending || assignClientGroupMutation.isPending,
  };
};
