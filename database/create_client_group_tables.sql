



drop table invitations;

drop table client_group_users;

drop table users;


CREATE TABLE `invitations` (
  `invitation_id` int NOT NULL AUTO_INCREMENT,
  `code` char(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT (substr(replace(uuid(),_utf8mb3'-',_utf8mb4''),1,16)),
  `expires_at` datetime NOT NULL,
  `client_group_id` int NOT NULL,
  PRIMARY KEY (`invitation_id`),
  UNIQUE KEY `uq_invitations_code` (`code`)
);

CREATE TABLE `client_group_users` (
  `client_group_id` int NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`client_group_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `client_group_users_ibfk_1` FOREIGN KEY (`client_group_id`) REFERENCES `client_groups` (`client_group_id`) ON DELETE CASCADE,
  CONSTRAINT `client_group_users_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
);

CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `sub` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `preferences` json DEFAULT NULL,
  `primary_client_group_id` int DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`)
);

