-- Create junction tables for client group security model

-- Table to link users to client groups (many-to-many)
CREATE TABLE IF NOT EXISTS client_group_users (
    client_group_id INT NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (client_group_id, user_id),
    FOREIGN KEY (client_group_id) REFERENCES client_groups(client_group_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Table to link entities to client groups (many-to-many)
CREATE TABLE IF NOT EXISTS client_group_entities (
    client_group_id INT NOT NULL,
    entity_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (client_group_id, entity_id),
    FOREIGN KEY (client_group_id) REFERENCES client_groups(client_group_id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Add indexes for better performance
CREATE INDEX idx_client_group_users_user_id ON client_group_users(user_id);
CREATE INDEX idx_client_group_entities_entity_id ON client_group_entities(entity_id);
