import { userPool } from "../config/cognito";

// Always use the production API endpoint
const API_BASE_URL = "https://api.onebor.com/panda";

// Client Groups
export interface ClientGroup {
  client_group_id: number;
  name: string;
  preferences?: any;
}

// Get the current user's token from Cognito
const getAuthToken = (): Promise<string | null> => {
  return new Promise((resolve) => {
    const currentUser = userPool.getCurrentUser();
    // console.log("🔍 getAuthToken - currentUser:", !!currentUser);
    if (!currentUser) {
      console.log("❌ getAuthToken - No current user");
      resolve(null);
      return;
    }

    // console.log(
    //   "🔍 getAuthToken - Getting session for user:",
    //   currentUser.getUsername()
    // );
    currentUser.getSession((err: any, session: any) => {
      // console.log("🔍 getAuthToken - Session callback:", {
      //   err: !!err,
      //   session: !!session,
      //   isValid: session?.isValid(),
      // });
      if (err) {
        console.log("❌ getAuthToken - Session error:", err);
        resolve(null);
        return;
      }
      if (!session || !session.isValid()) {
        console.log("❌ getAuthToken - Invalid session");
        resolve(null);
        return;
      }

      const idToken = session.getIdToken().getJwtToken();
      // console.log("✅ getAuthToken - Got token, length:", idToken.length);
      resolve(idToken);
    });
  });
};

// Base API call function with auth
const apiCall = async <T>(endpoint: string, data: any): Promise<T> => {
  // console.log("🚀 apiCall - Starting call to:", endpoint);
  const token = await getAuthToken();

  if (!token) {
    console.log("❌ apiCall - No authentication token available");
    throw new Error("No authentication token available");
  }

  const fullUrl = `${API_BASE_URL}${endpoint}`;
  // console.log("📡 apiCall - Making request to:", fullUrl);
  // console.log("📡 apiCall - Request data:", data);

  const response = await fetch(fullUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  // console.log("📡 apiCall - Response status:", response.status);
  if (!response.ok) {
    const errorText = await response.text();
    console.log("❌ apiCall - Error response:", errorText);
    throw new Error(`API call failed: ${response.status} ${errorText}`);
  }

  const result = await response.json();
  // console.log("✅ apiCall - Success:", endpoint);
  return result;
};

// Entity Types
export interface EntityType {
  entity_type_id: number;
  name: string;
  short_label?: string;
  label_color?: string;
  attributes_schema: any;
}

export interface CreateEntityTypeRequest {
  name: string;
  attributes_schema: any;
  short_label?: string;
  label_color?: string;
}

export interface QueryEntityTypesRequest {
  count_only?: boolean;
  limit?: number;
  offset?: number;
}

export type QueryEntityTypesResponse = EntityType[];

// Entities
export interface Entity {
  entity_id: number;
  name: string;
  entity_type_id: number;
  parent_entity_id: number | null;
  attributes: any;
}

export interface CreateEntityRequest {
  user_id: number; // Required for data protection
  client_group_id: number; // Required for data protection
  name: string;
  entity_type_id: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface UpdateEntityRequest {
  user_id: number; // Required for data protection
  entity_id?: number; // If passed, update existing entity; if not passed, create new entity
  client_group_id?: number; // Required for creating new entities
  name?: string;
  entity_type_id?: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface QueryEntitiesRequest {
  user_id: number; // Required for data protection
  entity_id?: number; // If passed, return only matching entity
  name?: string; // If ends with %, return all starting with string; else exact match
  entity_type_id?: number; // Filter by entity type
  parent_entity_id?: number | null; // Filter by parent entity
}

export type QueryEntitiesResponse = Entity[];

// API functions
export const createEntityType = async (
  data: CreateEntityTypeRequest
): Promise<EntityType> => {
  return apiCall<EntityType>("/create_entity_type", data);
};

export const queryEntityTypes = async (
  data: QueryEntityTypesRequest
): Promise<QueryEntityTypesResponse> => {
  return apiCall<QueryEntityTypesResponse>("/get_entity_types", data);
};

export const createEntity = async (
  data: CreateEntityRequest
): Promise<Entity> => {
  return apiCall<Entity>("/update_entity", data);
};

export const queryEntities = async (
  data: QueryEntitiesRequest
): Promise<QueryEntitiesResponse> => {
  return apiCall<QueryEntitiesResponse>("/get_entities", data);
};

export const updateEntity = async (
  data: UpdateEntityRequest
): Promise<Entity> => {
  return apiCall<Entity>("/update_entity", data);
};

export const updateEntityType = async (
  data: CreateEntityTypeRequest & { entity_type_id?: number }
): Promise<EntityType> => {
  return apiCall<EntityType>("/update_entity_type", data);
};

// Delete record function
export const deleteRecord = async (
  recordId: number | string,
  recordType: string
): Promise<{ success: boolean; message: string }> => {
  return apiCall<{ success: boolean; message: string }>("/delete_record", {
    record_id: recordId,
    record_type: recordType,
  });
};

// Users
export interface User {
  user_id: number; // Auto-increment integer
  sub: string; // Cognito user ID (required)
  email: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface CreateUserRequest {
  sub: string; // Cognito user ID (required)
  email: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface UpdateUserRequest {
  user_id?: number; // Database user ID (for existing users)
  sub?: string; // Cognito user ID (preferred lookup)
  email?: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface QueryUsersRequest {
  user_id?: number; // Database user ID
  sub?: string; // Cognito user ID
  email?: string;
  requesting_user_id?: number; // For access control - only see users in shared client groups
}

export type QueryUsersResponse = User[];

// Client Groups (moved to top of file)

export interface CreateClientGroupRequest {
  name: string;
  preferences?: any;
  user_id?: number;
}

export interface UpdateClientGroupRequest {
  client_group_id?: number;
  name?: string;
  preferences?: any;
}

export interface QueryClientGroupsRequest {
  client_group_id?: number;
  user_id?: number;
  group_name?: string;
}

export type QueryClientGroupsResponse = ClientGroup[];

// User API functions
export const queryUsers = async (
  data: QueryUsersRequest
): Promise<QueryUsersResponse> => {
  return apiCall<QueryUsersResponse>("/get_users", data);
};

export const updateUser = async (
  data: UpdateUserRequest | CreateUserRequest
): Promise<{ success: boolean; user_id: number }> => {
  return apiCall<{ success: boolean; user_id: number }>("/update_user", data);
};

// Client Group API functions
export const queryClientGroups = async (
  data: QueryClientGroupsRequest
): Promise<QueryClientGroupsResponse> => {
  return apiCall<QueryClientGroupsResponse>("/get_client_groups", data);
};

export const updateClientGroup = async (
  data: UpdateClientGroupRequest | CreateClientGroupRequest
): Promise<{ success: boolean; id: number }> => {
  return apiCall<{ success: boolean; id: number }>(
    "/update_client_group",
    data
  );
};

export const createClientGroup = async (
  data: CreateClientGroupRequest
): Promise<{ success: boolean; id: number }> => {
  return apiCall<{ success: boolean; id: number }>(
    "/update_client_group",
    data
  );
};

// Invitation interfaces
export interface Invitation {
  invitation_id: number;
  code: string;
  expires_at: string;
  client_group_id: number;
}

export interface CreateInvitationRequest {
  action: "create";
  expires_at: string;
  client_group_id: number;
}

export interface GetInvitationRequest {
  action: "get";
  code?: string;
  client_group_id?: number;
}

export interface RedeemInvitationRequest {
  action: "redeem";
  code: string;
}

export type InvitationRequest =
  | CreateInvitationRequest
  | GetInvitationRequest
  | RedeemInvitationRequest;

export type InvitationResponse =
  | Invitation[]
  | { success: boolean; invitation_id: number; code: string }
  | {
      success: boolean;
      invitation_id: number;
      client_group_id: number;
    };

// Client Group Membership interfaces
export interface ModifyClientGroupMembershipRequest {
  client_group_id: number;
  user_id: number;
  add_or_remove: "add" | "remove";
}

// Client Group Membership API functions
export const modifyClientGroupMembership = async (
  data: ModifyClientGroupMembershipRequest
): Promise<{ success: boolean }> => {
  console.log(
    "🔧 API - modifyClientGroupMembership called with:",
    JSON.stringify(data, null, 2)
  );
  const result = await apiCall<{ success: boolean }>(
    "/modify_client_group_membership",
    data
  );
  console.log(
    "🔧 API - modifyClientGroupMembership result:",
    JSON.stringify(result, null, 2)
  );
  return result;
};

// Client Group Entities interfaces and API functions
export interface ModifyClientGroupEntitiesRequest {
  client_group_id: number;
  entity_ids: number[]; // Array of entity_ids that should be in the group
}

export interface ModifyClientGroupEntitiesResponse {
  success: boolean;
  added_count: number;
  removed_count: number;
  current_entity_ids: number[];
  desired_entity_ids: number[];
  entities_added: number[];
  entities_removed: number[];
}

export const modifyClientGroupEntities = async (
  data: ModifyClientGroupEntitiesRequest
): Promise<ModifyClientGroupEntitiesResponse> => {
  console.log(
    "🔧 API - modifyClientGroupEntities called with:",
    JSON.stringify(data, null, 2)
  );
  const result = await apiCall<ModifyClientGroupEntitiesResponse>(
    "/modify_client_group_entities",
    data
  );
  console.log(
    "🔧 API - modifyClientGroupEntities result:",
    JSON.stringify(result, null, 2)
  );
  return result;
};

export interface QueryClientGroupEntitiesRequest {
  client_group_id: number;
  user_id: number;
}

export const queryClientGroupEntities = async (
  data: QueryClientGroupEntitiesRequest
): Promise<number[]> => {
  // For now, we'll use the existing getPandaEntities endpoint with client_group_id filter
  // This returns entity objects, but we just need the IDs
  const result = await apiCall<any[]>("/get_entities", {
    client_group_id: data.client_group_id,
    user_id: data.user_id,
  });
  return result.map((entity) =>
    typeof entity === "object" ? entity.entity_id : entity
  );
};

export interface QueryEntityCountRequest {
  user_id: number;
  client_group_id?: number;
  entity_type_id?: number;
  parent_entity_id?: number;
}

export const queryEntityCount = async (
  data: QueryEntityCountRequest
): Promise<number> => {
  const result = await apiCall<number>("/get_entities", {
    ...data,
    count_only: true,
  });
  return result;
};

// Entity Types count
export const queryEntityTypeCount = async (): Promise<number> => {
  const result = await apiCall<number>("/get_entity_types", {
    count_only: true,
  });
  return result;
};

// Users count
export interface QueryUserCountRequest {
  requesting_user_id?: number;
  user_id?: number;
  sub?: string;
  email?: string;
}

export const queryUserCount = async (
  data: QueryUserCountRequest
): Promise<number> => {
  const result = await apiCall<number>("/get_users", {
    ...data,
    count_only: true,
  });
  return result;
};

// Client Groups count
export interface QueryClientGroupCountRequest {
  user_id?: number;
  client_group_id?: number;
  group_name?: string;
}

export const queryClientGroupCount = async (
  data: QueryClientGroupCountRequest
): Promise<number> => {
  const result = await apiCall<number>("/get_client_groups", {
    ...data,
    count_only: true,
  });
  return result;
};

// Invitations count
export interface QueryInvitationCountRequest {
  client_group_id?: number;
  code?: string;
}

export const queryInvitationCount = async (
  data: QueryInvitationCountRequest
): Promise<number> => {
  const result = await apiCall<number>("/manage_invitation", {
    action: "get",
    ...data,
    count_only: true,
  });
  return result;
};

// Invitation API functions
export const manageInvitation = async (
  data: InvitationRequest
): Promise<InvitationResponse> => {
  return apiCall<InvitationResponse>("/manage_invitation", data);
};

// Convenience function to update user's sub field after login
export const updateUserSub = async (
  sub: string,
  email: string
): Promise<{ success: boolean; user_id: number }> => {
  return updateUser({
    sub,
    email,
  });
};

// Utility function to parse and humanize API errors
export const parseApiError = (error: Error): string => {
  const message = error.message;

  // Handle API call errors with JSON responses
  if (message.includes("API call failed:")) {
    try {
      // Extract JSON from error message like "API call failed: 500 {"error": "..."}"
      const jsonMatch = message.match(/\{.*\}$/);
      if (jsonMatch) {
        const errorResponse = JSON.parse(jsonMatch[0]);
        const errorText = errorResponse.error || errorResponse.message;

        // Handle specific database errors
        if (typeof errorText === "string") {
          // Duplicate entry errors
          if (
            errorText.includes("Duplicate entry") &&
            errorText.includes("client_groups.name")
          ) {
            const nameMatch = errorText.match(/Duplicate entry '([^']+)'/);
            const orgName = nameMatch ? nameMatch[1] : "that name";
            return `That organization name "${orgName}" is already in use. Please try a different name.`;
          }

          // Other duplicate entry errors
          if (errorText.includes("Duplicate entry")) {
            return "This record already exists. Please check your input and try again.";
          }

          // Foreign key constraint errors
          if (errorText.includes("foreign key constraint")) {
            return "Unable to complete this action due to related data constraints.";
          }

          // Connection errors
          if (
            errorText.includes("connection") ||
            errorText.includes("timeout")
          ) {
            return "Connection error. Please check your internet connection and try again.";
          }

          // Access denied errors
          if (
            errorText.includes("Access denied") ||
            errorText.includes("permission")
          ) {
            return "You do not have permission to perform this action.";
          }
        }
      }
    } catch (parseError) {
      // If we can't parse the JSON, fall back to basic cleanup
    }
  }

  // Generic cleanup for other errors
  if (message.includes("API call failed:")) {
    return "An error occurred while processing your request. Please try again.";
  }

  // Return the original message if no specific handling applies
  return message;
};
