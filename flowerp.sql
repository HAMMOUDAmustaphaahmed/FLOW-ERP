-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : ven. 07 nov. 2025 à 16:00
-- Version du serveur : 10.4.32-MariaDB
-- Version de PHP : 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `flowerp`
--

-- --------------------------------------------------------

--
-- Structure de la table `companies`
--

CREATE TABLE `companies` (
  `id` int(11) NOT NULL,
  `name` varchar(200) NOT NULL,
  `legal_name` varchar(200) DEFAULT NULL,
  `tax_id` varchar(50) DEFAULT NULL,
  `registration_number` varchar(50) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `postal_code` varchar(20) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `website` varchar(200) DEFAULT NULL,
  `industry` varchar(100) DEFAULT NULL,
  `employee_count` int(11) DEFAULT NULL,
  `founded_date` date DEFAULT NULL,
  `logo_url` varchar(255) DEFAULT NULL,
  `currency` varchar(3) DEFAULT NULL,
  `timezone` varchar(50) DEFAULT NULL,
  `language` varchar(5) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `companies`
--

INSERT INTO `companies` (`id`, `name`, `legal_name`, `tax_id`, `registration_number`, `address`, `city`, `state`, `postal_code`, `country`, `phone`, `email`, `website`, `industry`, `employee_count`, `founded_date`, `logo_url`, `currency`, `timezone`, `language`, `is_active`, `created_at`, `updated_at`, `created_by_id`) VALUES
(1, 'Ma societe', 'Limité', '1234/A/M/000', 'B123456', '123 Avenue Habib Bourguiba', 'Tunis', 'Tunis', '1000', 'Tunisie', '+21671234567', 'contact@masociete.tn', 'https://www.masociete.tn', 'technology', NULL, '2025-11-06', NULL, 'TND', 'Africa/Tunis', 'fr', 1, '2025-11-06 13:16:51', '2025-11-06 13:16:51', 1);

-- --------------------------------------------------------

--
-- Structure de la table `departments`
--

CREATE TABLE `departments` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `company_id` int(11) NOT NULL,
  `parent_id` int(11) DEFAULT NULL,
  `manager_id` int(11) DEFAULT NULL,
  `budget` decimal(15,2) DEFAULT NULL,
  `budget_spent` decimal(15,2) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `manager_can_add_users` tinyint(1) DEFAULT 1,
  `manager_can_edit_budget` tinyint(1) DEFAULT 0,
  `manager_can_create_tables` tinyint(1) DEFAULT 1,
  `manager_can_delete_items` tinyint(1) DEFAULT 1,
  `deleted_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `departments`
--

INSERT INTO `departments` (`id`, `name`, `code`, `description`, `company_id`, `parent_id`, `manager_id`, `budget`, `budget_spent`, `is_active`, `created_at`, `updated_at`, `manager_can_add_users`, `manager_can_edit_budget`, `manager_can_create_tables`, `manager_can_delete_items`, `deleted_at`) VALUES
(1, 'sdvsdv', 'sdvsdv', 'sdvsdvsd', 2, NULL, NULL, 1.00, 0.00, 1, '2025-11-06 13:18:35', '2025-11-06 13:18:35', 1, 0, 1, 1, NULL),
(2, 'fbgfb', 'gbgb', 'gbgbgbg', 2, NULL, NULL, 2.00, 0.00, 1, '2025-11-06 13:23:23', '2025-11-06 13:23:23', 1, 0, 1, 1, NULL),
(3, 'qdsvc', 'sdc', 'sdc', 2, NULL, NULL, 2.00, 0.00, 1, '2025-11-06 13:29:02', '2025-11-06 13:29:02', 1, 0, 1, 1, NULL),
(4, 'Informatique', 'IT', 'test', 1, NULL, NULL, 1.00, 0.00, 1, '2025-11-07 11:43:12', '2025-11-07 14:57:52', 1, 0, 1, 1, '2025-11-07 14:57:52'),
(5, 'rge', 'erg', 'dfvdfv', 1, NULL, NULL, 95.00, 0.00, 1, '2025-11-07 14:58:06', '2025-11-07 14:58:06', 1, 0, 1, 1, NULL);

-- --------------------------------------------------------

--
-- Structure de la table `department_fields`
--

CREATE TABLE `department_fields` (
  `id` int(11) NOT NULL,
  `department_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `field_type` varchar(50) NOT NULL,
  `is_required` tinyint(1) DEFAULT NULL,
  `default_value` text DEFAULT NULL,
  `options` text DEFAULT NULL,
  `order` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `department_items`
--

CREATE TABLE `department_items` (
  `id` int(11) NOT NULL,
  `department_id` int(11) NOT NULL,
  `item_type` varchar(50) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `data` text DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL,
  `updated_by_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `department_tables`
--

CREATE TABLE `department_tables` (
  `id` int(11) NOT NULL,
  `department_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `display_name` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `icon` varchar(50) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `allow_import` tinyint(1) DEFAULT NULL,
  `allow_export` tinyint(1) DEFAULT NULL,
  `view_permission` varchar(50) DEFAULT NULL,
  `edit_permission` varchar(50) DEFAULT NULL,
  `delete_permission` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `department_tables`
--

INSERT INTO `department_tables` (`id`, `department_id`, `name`, `display_name`, `description`, `icon`, `is_active`, `allow_import`, `allow_export`, `view_permission`, `edit_permission`, `delete_permission`, `created_at`, `updated_at`, `created_by_id`) VALUES
(1, 4, 'pc', 'Ordinateurs', 'test', 'desktop', 0, 1, 1, 'department', 'department', 'manager_only', '2025-11-07 11:53:38', '2025-11-07 13:41:00', 1),
(2, 4, 'dscsd', 'cvsdcsdcsd', 'csdcsdcsdc', 'table', 1, 1, 1, 'department', 'department', 'manager_only', '2025-11-07 14:49:03', '2025-11-07 14:49:03', 1),
(3, 5, 'vdfvdf', 'vdfvdfvdfv', 'dfvdf', 'table', 1, 1, 1, 'department', 'department', 'manager_only', '2025-11-07 14:58:27', '2025-11-07 14:58:27', 1),
(4, 5, 'dfvdfv', 'dfvdf', 'vdfvdfvdfv', 'table', 1, 1, 1, 'department', 'department', 'manager_only', '2025-11-07 14:58:48', '2025-11-07 14:58:48', 1);

-- --------------------------------------------------------

--
-- Structure de la table `login_attempts`
--

CREATE TABLE `login_attempts` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `ip_address` varchar(45) NOT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `success` tinyint(1) DEFAULT NULL,
  `failure_reason` varchar(100) DEFAULT NULL,
  `timestamp` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `login_attempts`
--

INSERT INTO `login_attempts` (`id`, `username`, `ip_address`, `user_agent`, `success`, `failure_reason`, `timestamp`) VALUES
(1, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-05 12:40:56'),
(2, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-05 14:40:45'),
(3, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-06 13:40:11'),
(4, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-06 13:54:17');

-- --------------------------------------------------------

--
-- Structure de la table `sessions`
--

CREATE TABLE `sessions` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `session_token` varchar(255) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `last_activity` datetime DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `table_columns`
--

CREATE TABLE `table_columns` (
  `id` int(11) NOT NULL,
  `table_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `display_name` varchar(200) NOT NULL,
  `data_type` varchar(50) NOT NULL,
  `type_config` text DEFAULT NULL,
  `is_required` tinyint(1) DEFAULT NULL,
  `is_unique` tinyint(1) DEFAULT NULL,
  `default_value` text DEFAULT NULL,
  `validation_rules` text DEFAULT NULL,
  `order` int(11) DEFAULT NULL,
  `width` int(11) DEFAULT NULL,
  `is_visible` tinyint(1) DEFAULT NULL,
  `is_sortable` tinyint(1) DEFAULT NULL,
  `is_filterable` tinyint(1) DEFAULT NULL,
  `display_format` varchar(100) DEFAULT NULL,
  `prefix` varchar(20) DEFAULT NULL,
  `suffix` varchar(20) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `table_columns`
--

INSERT INTO `table_columns` (`id`, `table_id`, `name`, `display_name`, `data_type`, `type_config`, `is_required`, `is_unique`, `default_value`, `validation_rules`, `order`, `width`, `is_visible`, `is_sortable`, `is_filterable`, `display_format`, `prefix`, `suffix`, `created_at`) VALUES
(1, 1, 'marque', 'Marque', 'text', NULL, 0, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 11:53:38'),
(2, 2, 'sdc', 'sdcs', 'text', NULL, 0, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 14:49:03'),
(3, 3, 'dfv', 'dfvdf', 'text', NULL, 1, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 14:58:27'),
(4, 3, 'dfvdf', 'vdfvdfv', 'text', NULL, 0, 0, NULL, NULL, 1, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 14:58:27'),
(5, 3, 'dfvdf', 'vdfv', 'text', NULL, 0, 0, NULL, NULL, 2, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 14:58:27'),
(6, 4, 'dfv', 'dfvdf', 'text', NULL, 0, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-07 14:58:48');

-- --------------------------------------------------------

--
-- Structure de la table `table_rows`
--

CREATE TABLE `table_rows` (
  `id` int(11) NOT NULL,
  `table_id` int(11) NOT NULL,
  `data` text NOT NULL,
  `row_order` int(11) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL,
  `updated_by_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `table_rows`
--

INSERT INTO `table_rows` (`id`, `table_id`, `data`, `row_order`, `is_active`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id`) VALUES
(2, 1, '{\"marque\": \"test\"}', 0, 1, '2025-11-07 13:40:44', '2025-11-07 13:40:44', 1, NULL),
(3, 4, '{\"dfv\": \"vdfvdf\"}', 0, 1, '2025-11-07 14:58:56', '2025-11-07 14:58:56', 1, NULL);

-- --------------------------------------------------------

--
-- Structure de la table `table_templates`
--

CREATE TABLE `table_templates` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `display_name` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `icon` varchar(50) DEFAULT NULL,
  `template_config` text NOT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `last_name` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `is_admin` tinyint(1) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `role` varchar(50) DEFAULT NULL,
  `failed_login_attempts` int(11) DEFAULT NULL,
  `account_locked_until` datetime DEFAULT NULL,
  `password_changed_at` datetime DEFAULT NULL,
  `two_factor_enabled` tinyint(1) DEFAULT NULL,
  `two_factor_secret` varchar(32) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `last_login` datetime DEFAULT NULL,
  `last_ip` varchar(45) DEFAULT NULL,
  `company_id` int(11) DEFAULT NULL,
  `department_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `first_name`, `last_name`, `phone`, `is_admin`, `is_active`, `role`, `failed_login_attempts`, `account_locked_until`, `password_changed_at`, `two_factor_enabled`, `two_factor_secret`, `created_at`, `updated_at`, `last_login`, `last_ip`, `company_id`, `department_id`) VALUES
(1, 'HammoudaAhmed', 'ahmedmustapha.hammouda@gmail.com', 'scrypt:32768:8:1$zjf9oGnhdDzuMH7r$6ed7150d7bc973f95513711c97e431f016964bc4c0fa20afed9a255c3b28425f2b9766fdaa2baa8d05ac30fcb4d1347cab0cd1859b91b168ec3f788e6d2df18b', 'ahmed', 'hammouda', NULL, 1, 1, 'admin', 0, NULL, NULL, NULL, NULL, '2025-11-05 12:40:18', '2025-11-06 13:54:17', '2025-11-06 13:54:17', '192.168.213.43', 1, NULL);

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `companies`
--
ALTER TABLE `companies`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`),
  ADD UNIQUE KEY `tax_id` (`tax_id`),
  ADD KEY `created_by_id` (`created_by_id`);

--
-- Index pour la table `departments`
--
ALTER TABLE `departments`
  ADD PRIMARY KEY (`id`),
  ADD KEY `manager_id` (`manager_id`),
  ADD KEY `company_id` (`company_id`),
  ADD KEY `parent_id` (`parent_id`);

--
-- Index pour la table `department_fields`
--
ALTER TABLE `department_fields`
  ADD PRIMARY KEY (`id`),
  ADD KEY `department_id` (`department_id`);

--
-- Index pour la table `department_items`
--
ALTER TABLE `department_items`
  ADD PRIMARY KEY (`id`),
  ADD KEY `created_by_id` (`created_by_id`),
  ADD KEY `idx_dept_item_type` (`department_id`,`item_type`),
  ADD KEY `fk_dept_items_updated_by` (`updated_by_id`);

--
-- Index pour la table `department_tables`
--
ALTER TABLE `department_tables`
  ADD PRIMARY KEY (`id`),
  ADD KEY `department_id` (`department_id`),
  ADD KEY `created_by_id` (`created_by_id`);

--
-- Index pour la table `login_attempts`
--
ALTER TABLE `login_attempts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_login_attempts_timestamp` (`timestamp`),
  ADD KEY `ix_login_attempts_username` (`username`);

--
-- Index pour la table `sessions`
--
ALTER TABLE `sessions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_sessions_session_token` (`session_token`),
  ADD KEY `user_id` (`user_id`);

--
-- Index pour la table `table_columns`
--
ALTER TABLE `table_columns`
  ADD PRIMARY KEY (`id`),
  ADD KEY `table_id` (`table_id`);

--
-- Index pour la table `table_rows`
--
ALTER TABLE `table_rows`
  ADD PRIMARY KEY (`id`),
  ADD KEY `created_by_id` (`created_by_id`),
  ADD KEY `updated_by_id` (`updated_by_id`),
  ADD KEY `idx_table_active` (`table_id`,`is_active`);

--
-- Index pour la table `table_templates`
--
ALTER TABLE `table_templates`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Index pour la table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_username` (`username`),
  ADD UNIQUE KEY `ix_users_email` (`email`),
  ADD KEY `department_id` (`department_id`),
  ADD KEY `company_id` (`company_id`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `companies`
--
ALTER TABLE `companies`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `departments`
--
ALTER TABLE `departments`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT pour la table `department_fields`
--
ALTER TABLE `department_fields`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `department_items`
--
ALTER TABLE `department_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `department_tables`
--
ALTER TABLE `department_tables`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `login_attempts`
--
ALTER TABLE `login_attempts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `sessions`
--
ALTER TABLE `sessions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `table_columns`
--
ALTER TABLE `table_columns`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT pour la table `table_rows`
--
ALTER TABLE `table_rows`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT pour la table `table_templates`
--
ALTER TABLE `table_templates`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `companies`
--
ALTER TABLE `companies`
  ADD CONSTRAINT `companies_ibfk_1` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `departments`
--
ALTER TABLE `departments`
  ADD CONSTRAINT `departments_ibfk_1` FOREIGN KEY (`manager_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `departments_ibfk_2` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`),
  ADD CONSTRAINT `departments_ibfk_3` FOREIGN KEY (`parent_id`) REFERENCES `departments` (`id`);

--
-- Contraintes pour la table `department_fields`
--
ALTER TABLE `department_fields`
  ADD CONSTRAINT `department_fields_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`);

--
-- Contraintes pour la table `department_items`
--
ALTER TABLE `department_items`
  ADD CONSTRAINT `department_items_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  ADD CONSTRAINT `department_items_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `fk_dept_items_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Contraintes pour la table `department_tables`
--
ALTER TABLE `department_tables`
  ADD CONSTRAINT `department_tables_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  ADD CONSTRAINT `department_tables_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `sessions`
--
ALTER TABLE `sessions`
  ADD CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `table_columns`
--
ALTER TABLE `table_columns`
  ADD CONSTRAINT `table_columns_ibfk_1` FOREIGN KEY (`table_id`) REFERENCES `department_tables` (`id`);

--
-- Contraintes pour la table `table_rows`
--
ALTER TABLE `table_rows`
  ADD CONSTRAINT `table_rows_ibfk_1` FOREIGN KEY (`table_id`) REFERENCES `department_tables` (`id`),
  ADD CONSTRAINT `table_rows_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `table_rows_ibfk_3` FOREIGN KEY (`updated_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `users_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  ADD CONSTRAINT `users_ibfk_2` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
