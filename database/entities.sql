USE onebor;

-- Drop tables if they already exist (careful in production)
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS entity_types;

-- Create entity_types table
CREATE TABLE entity_types (
  entity_type_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  attributes_schema JSON NULL
) ENGINE=InnoDB;

-- Create entities table
CREATE TABLE entities (
  entity_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  entity_type_id INT NOT NULL,
  parent_entity_id INT NULL,
  attributes JSON NULL,
  CONSTRAINT fk_entities_entity_type
    FOREIGN KEY (entity_type_id) REFERENCES entity_types(entity_type_id),
  CONSTRAINT fk_entities_parent
    FOREIGN KEY (parent_entity_id) REFERENCES entities(entity_id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

-- Populate entity_types
INSERT INTO entity_types (name, attributes_schema) VALUES
  ('Investor', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Investor",
  "type": "object",
  "properties": {
    "first_name": { "type": "string" },
    "last_name": { "type": "string" },
    "email": { "type": "string", "format": "email" },
    "phone": { "type": "string" },
    "address": { "type": "string" },
    "accreditation_status": { "type": "string", "enum": ["Accredited", "Non-Accredited"] }
  },
  "required": ["first_name", "last_name"]
}'),
  ('Trust', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Trust",
  "type": "object",
  "properties": {
    "legal_name": { "type": "string" },
    "registration_number": { "type": "string" },
    "address": { "type": "string" },
    "contact_email": { "type": "string", "format": "email" }
  },
  "required": ["legal_name"]
}'),
  ('Account', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Account",
  "type": "object",
  "properties": {
    "account_number": { "type": "string" },
    "institution_name": { "type": "string" },
    "currency_code": { "type": "string" },
    "opened_date": { "type": "string", "format": "date" }
  },
  "required": ["account_number", "currency_code"]
}'),
  ('Vehicle', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Vehicle",
  "type": "object",
  "properties": {
    "vehicle_name": { "type": "string" },
    "inception_date": { "type": "string", "format": "date" }
  },
  "required": ["vehicle_name"]
}'),
  ('Fund', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Fund",
  "type": "object",
  "properties": {
    "inception_date": { "type": "string", "format": "date" }
  }
}'),
  ('Equity', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Equity",
  "type": "object",
  "properties": {
    "isin": { "type": "string" },
    "cusip": { "type": "string" },
    "sedol": { "type": "string" },
    "ticker": { "type": "string" },
    "issue_currency": { "type": "string" },
    "issue_date": { "type": "string", "format": "date" },
    "issuer": { "type": "string" },
    "issue_country": { "type": "string" },
    "share_class": { "type": "string" }
  }
}'),
  ('Bond', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Bond",
  "type": "object",
  "properties": {
    "isin": { "type": "string" },
    "cusip": { "type": "string" },
    "sedol": { "type": "string" },
    "ticker": { "type": "string" },
    "issue_currency": { "type": "string" },
    "issue_date": { "type": "string", "format": "date" },
    "issuer": { "type": "string" },
    "issue_country": { "type": "string" },
    "bond_type": { "type": "string" },
    "coupon_type": { "type": "string" },
    "coupon_rate": { "type": "number" },
    "coupon_frequency": { "type": "string" },
    "day_count": { "type": "string" },
    "maturity_date": { "type": "string", "format": "date" },
    "face_value": { "type": "number" }
  }
}'),
  ('ETF', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ETF",
  "type": "object",
  "properties": {
    "isin": { "type": "string" },
    "cusip": { "type": "string" },
    "sedol": { "type": "string" },
    "ticker": { "type": "string" },
    "issue_currency": { "type": "string" },
    "issue_date": { "type": "string", "format": "date" },
    "issuer": { "type": "string" },
    "issue_country": { "type": "string" },
    "fund_sponsor": { "type": "string" }
  }
}'),
  ('Currency', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Currency",
  "type": "object",
  "properties": {
    "currency_code": { "type": "string", "pattern": "^[A-Z]{3}$" },
    "issue_country": { "type": "string" }
  },
  "required": ["currency_code", "issue_country"]
}'),
  ('Holding', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Holding",
  "type": "object"
}'),
  ('Option', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Option",
  "type": "object",
  "properties": {
    "underlying_entity_id": { "type": "number" },
    "ticker": { "type": "string" },
    "issue_currency": { "type": "string" },
    "option_type": { "type": "string", "enum": ["Call", "Put"] },
    "style": { "type": "string", "enum": ["European", "American"] },
    "strike_price": { "type": "number" },
    "expiry_date": { "type": "string", "format": "date" },
    "contract_size": { "type": "number" }
  },
  "required": ["underlying_ticker", "option_type", "strike_price", "expiry_date"]
}'),
  ('Future', '{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Future",
  "type": "object",
  "properties": {
    "contract_code": { "type": "string" },
    "underlying_entity_id": { "type": "number" },
    "exchange": { "type": "string" },
    "expiry_date": { "type": "string", "format": "date" },
    "contract_size": { "type": "number" },
    "issue_currency": { "type": "string" }
  },
  "required": ["contract_code", "expiry_date", "contract_size"]
}');

select * from entity_types;
