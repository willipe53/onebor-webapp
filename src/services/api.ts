import { userPool } from "../config/cognito";

const API_BASE_URL = "/api"; // Use proxy in development

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
    if (!currentUser) {
      resolve(null);
      return;
    }

    currentUser.getSession((err: any, session: any) => {
      if (err || !session || !session.isValid()) {
        resolve(null);
        return;
      }

      const idToken = session.getIdToken().getJwtToken();
      resolve(idToken);
    });
  });
};

// Base API call function with auth
const apiCall = async <T>(endpoint: string, data: any): Promise<T> => {
  const token = await getAuthToken();

  if (!token) {
    throw new Error("No authentication token available");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API call failed: ${response.status} ${errorText}`);
  }

  return response.json();
};

// Entity Types
export interface EntityType {
  entity_type_id: number;
  name: string;
  attributes_schema: any;
}

export interface CreateEntityTypeRequest {
  name: string;
  attributes_schema: any;
  short_label?: string;
  label_color?: string;
}

export interface QueryEntityTypesRequest {
  // No parameters needed - always returns all entity types
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
  user_id: string; // Required for data protection
  client_group_id: number; // Required for data protection
  name: string;
  entity_type_id: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface UpdateEntityRequest {
  user_id: string; // Required for data protection
  entity_id?: number; // If passed, update existing entity; if not passed, create new entity
  client_group_id?: number; // Required for creating new entities
  name?: string;
  entity_type_id?: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface QueryEntitiesRequest {
  user_id: string; // Required for data protection
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

// Users
export interface User {
  user_id: string;
  email: string;
  name: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface CreateUserRequest {
  user_id?: string;
  email: string;
  name: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface UpdateUserRequest {
  user_id: string;
  email?: string;
  name?: string;
  preferences?: any;
  primary_client_group_id?: number;
}

export interface QueryUsersRequest {
  user_id?: string;
  email?: string;
  name?: string;
}

export type QueryUsersResponse = User[];

// Client Groups (moved to top of file)

export interface CreateClientGroupRequest {
  name: string;
  preferences?: any;
}

export interface UpdateClientGroupRequest {
  client_group_id?: number;
  name?: string;
  preferences?: any;
}

export interface QueryClientGroupsRequest {
  client_group_id?: number;
  user_id?: string;
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
): Promise<{ success: boolean; user_id: string }> => {
  return apiCall<{ success: boolean; user_id: string }>("/update_user", data);
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

// Invitation interfaces
export interface Invitation {
  invitation_id: string;
  email: string;
  name: string | null;
  code: string;
  expires_at: string;
  redeemed: boolean;
  primary_client_group_id: number;
}

export interface CreateInvitationRequest {
  action: "create";
  email: string;
  name?: string;
  expires_at: string;
  primary_client_group_id: number;
}

export interface GetInvitationRequest {
  action: "get";
  email?: string;
  primary_client_group_id?: number;
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
  | { success: boolean; invitation_id: string; code: string }
  | {
      success: boolean;
      invitation_id: string;
      email: string;
      name: string;
      primary_client_group_id: number;
    };

// Client Group Membership interfaces
export interface ModifyClientGroupMembershipRequest {
  client_group_id: number;
  user_id: string;
  add_or_remove: "add" | "remove";
}

// Client Group Membership API functions
export const modifyClientGroupMembership = async (
  data: ModifyClientGroupMembershipRequest
): Promise<{ success: boolean }> => {
  return apiCall<{ success: boolean }>("/modify_client_group_membership", data);
};

// Invitation API functions
export const manageInvitation = async (
  data: InvitationRequest
): Promise<InvitationResponse> => {
  return apiCall<InvitationResponse>("/manage_invitation", data);
};
