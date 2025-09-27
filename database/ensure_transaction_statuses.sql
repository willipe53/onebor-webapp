-- Ensure the required transaction statuses exist
-- This script can be run to set up the correct transaction statuses

INSERT IGNORE INTO transaction_statuses (transaction_status_id, name) VALUES
(1, 'INCOMPLETE'),
(2, 'QUEUED'),
(3, 'PROCESSED');

-- Verify the statuses were created
SELECT * FROM transaction_statuses ORDER BY transaction_status_id;
