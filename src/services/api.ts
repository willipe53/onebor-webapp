import { userPool } from "../config/cognito";

const API_BASE_URL = "/api"; // Use proxy in development

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
  name: string;
  entity_type_id: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface UpdateEntityRequest {
  entity_id?: number; // If passed, update existing entity; if not passed, create new entity
  name?: string;
  entity_type_id?: number;
  parent_entity_id?: number | null;
  attributes?: any;
}

export interface QueryEntitiesRequest {
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
