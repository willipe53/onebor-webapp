-- Add email_sent_to column to invitations table
-- This column will store the email address that the invitation was sent to

ALTER TABLE invitations 
ADD COLUMN email_sent_to VARCHAR(255) NULL 
COMMENT 'Email address that the invitation was sent to';

-- Optional: Add an index on email_sent_to for faster lookups
CREATE INDEX idx_invitations_email_sent_to ON invitations(email_sent_to);

-- Verify the column was added
DESCRIBE invitations;

