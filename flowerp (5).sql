-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : 127.0.0.1
-- Généré le : lun. 17 nov. 2025 à 16:11
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

DELIMITER $$
--
-- Procédures
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_get_approver_statistics` (IN `p_approver_id` INT)   BEGIN
    SELECT 
        COUNT(*) as total_requests,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
        SUM(CASE WHEN is_in_blockchain = 1 THEN 1 ELSE 0 END) as in_blockchain
    FROM employee_requests
    WHERE approved_by_id = p_approver_id
    OR expected_approver_id = p_approver_id;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_get_pending_requests_for_approver` (IN `p_approver_id` INT)   BEGIN
    SELECT 
        id,
        type,
        requester_name,
        requester_department,
        created_at,
        CASE 
            WHEN type = 'leave' THEN CONCAT(days, ' jours du ', start_date, ' au ', end_date)
            WHEN type = 'loan' THEN CONCAT(amount, ' TND')
            ELSE '-'
        END as details,
        reason
    FROM v_employee_requests_hierarchy
    WHERE expected_approver_id = p_approver_id
    AND status = 'pending'
    ORDER BY created_at ASC;
END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `attendances`
--

CREATE TABLE `attendances` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `date` date NOT NULL,
  `check_in` time DEFAULT NULL,
  `check_out` time DEFAULT NULL,
  `hours_worked` float DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `is_justified` tinyint(1) DEFAULT NULL,
  `justification` text DEFAULT NULL,
  `deduction_amount` decimal(10,3) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `chat_conversations`
--

CREATE TABLE `chat_conversations` (
  `id` int(11) NOT NULL,
  `user1_id` int(11) NOT NULL,
  `user2_id` int(11) NOT NULL,
  `last_message_preview` varchar(200) DEFAULT NULL,
  `last_message_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `chat_conversations`
--

INSERT INTO `chat_conversations` (`id`, `user1_id`, `user2_id`, `last_message_preview`, `last_message_at`, `created_at`) VALUES
(1, 1, 4, 'sdcsdcsdcsdc', '2025-11-17 13:01:52', '2025-11-17 12:55:27'),
(2, 1, 2, 'sdcsdc', '2025-11-17 15:08:57', '2025-11-17 13:02:05'),
(3, 1, 3, 'dsvsdv', '2025-11-17 15:09:05', '2025-11-17 15:09:02');

-- --------------------------------------------------------

--
-- Structure de la table `chat_files`
--

CREATE TABLE `chat_files` (
  `id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `filepath` varchar(500) NOT NULL,
  `file_size` int(11) DEFAULT NULL,
  `mime_type` varchar(100) DEFAULT NULL,
  `conversation_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `uploaded_at` datetime DEFAULT NULL,
  `uploaded_by_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `chat_groups`
--

CREATE TABLE `chat_groups` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `last_message_preview` varchar(200) DEFAULT NULL,
  `last_message_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `chat_groups`
--

INSERT INTO `chat_groups` (`id`, `name`, `description`, `avatar_url`, `last_message_preview`, `last_message_at`, `created_at`, `created_by_id`) VALUES
(1, 'sdcsd', 'sdc', NULL, NULL, NULL, '2025-11-17 09:36:23', 1),
(2, 'sdc', 'dcccc', NULL, 'csdcdcs', '2025-11-17 13:01:48', '2025-11-17 13:01:36', 1);

-- --------------------------------------------------------

--
-- Structure de la table `chat_group_members`
--

CREATE TABLE `chat_group_members` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `is_admin` tinyint(1) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `muted` tinyint(1) DEFAULT NULL,
  `joined_at` datetime DEFAULT NULL,
  `left_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `chat_group_members`
--

INSERT INTO `chat_group_members` (`id`, `group_id`, `user_id`, `is_admin`, `is_active`, `muted`, `joined_at`, `left_at`) VALUES
(1, 1, 1, 1, 1, 0, '2025-11-17 09:36:23', NULL),
(2, 2, 1, 1, 1, 0, '2025-11-17 13:01:36', NULL);

-- --------------------------------------------------------

--
-- Structure de la table `chat_messages`
--

CREATE TABLE `chat_messages` (
  `id` int(11) NOT NULL,
  `conversation_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `sender_id` int(11) NOT NULL,
  `content` text NOT NULL,
  `message_type` varchar(50) DEFAULT NULL,
  `file_id` int(11) DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT NULL,
  `read_at` datetime DEFAULT NULL,
  `is_deleted` tinyint(1) DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `reactions` text DEFAULT NULL,
  `reply_to_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `chat_messages`
--

INSERT INTO `chat_messages` (`id`, `conversation_id`, `group_id`, `sender_id`, `content`, `message_type`, `file_id`, `is_read`, `read_at`, `is_deleted`, `deleted_at`, `reactions`, `reply_to_id`, `created_at`, `updated_at`) VALUES
(1, 1, NULL, 1, 'sdcsd', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 13:01:23', '2025-11-17 13:01:23'),
(2, 1, NULL, 1, 'sdcsdc', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 13:01:27', '2025-11-17 13:01:27'),
(3, 1, NULL, 1, 'sdcsdc', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 13:01:28', '2025-11-17 13:01:28'),
(4, NULL, 2, 1, 'csdcdcs', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 13:01:48', '2025-11-17 13:01:48'),
(5, 1, NULL, 1, 'sdcsdcsdcsdc', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 13:01:52', '2025-11-17 13:01:52'),
(6, 2, NULL, 1, 'sdcsdc', 'text', NULL, 1, '2025-11-17 15:09:25', 0, NULL, NULL, NULL, '2025-11-17 15:08:57', '2025-11-17 15:09:25'),
(7, 3, NULL, 1, 'dsvsdv', 'text', NULL, 0, NULL, 0, NULL, NULL, NULL, '2025-11-17 15:09:05', '2025-11-17 15:09:05');

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
(1, '', '', NULL, NULL, '', '', NULL, NULL, 'Tunisie', '', 'ahmedmustapha.hammouda@gmail.com', NULL, '', NULL, NULL, NULL, 'TND', 'Africa/Tunis', 'fr', 1, '2025-11-10 09:34:54', '2025-11-10 09:34:54', 1);

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
  `manager_can_add_users` tinyint(1) DEFAULT NULL,
  `manager_can_edit_budget` tinyint(1) DEFAULT NULL,
  `manager_can_create_tables` tinyint(1) DEFAULT NULL,
  `manager_can_delete_items` tinyint(1) DEFAULT NULL,
  `budget` decimal(15,2) DEFAULT NULL,
  `budget_spent` decimal(15,2) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `departments`
--

INSERT INTO `departments` (`id`, `name`, `code`, `description`, `company_id`, `parent_id`, `manager_id`, `manager_can_add_users`, `manager_can_edit_budget`, `manager_can_create_tables`, `manager_can_delete_items`, `budget`, `budget_spent`, `is_active`, `created_at`, `updated_at`, `deleted_at`) VALUES
(1, 'Informatique', 'IT', 'sdcsc', 1, NULL, NULL, 1, 0, 1, 1, 1.00, 0.00, 1, '2025-11-10 11:34:21', '2025-11-10 15:02:18', NULL),
(2, 'Ressources Humaines', 'RH', 'sdcsdc', 1, NULL, 4, 1, 0, 1, 1, 1.00, 0.00, 1, '2025-11-10 11:42:30', '2025-11-17 07:12:07', NULL),
(3, 'Maintenance', 'MNTN', '', 1, NULL, 5, 1, 0, 1, 1, 2.00, 0.00, 1, '2025-11-10 15:02:50', '2025-11-13 14:00:35', NULL),
(4, 'Achats', 'ACHT', '', 1, NULL, NULL, 1, 0, 1, 1, 3.00, 0.00, 1, '2025-11-10 15:04:08', '2025-11-10 15:04:08', NULL),
(5, 'test', 'test', 'jdfh', 1, NULL, NULL, 1, 0, 1, 1, 3.00, 0.00, 1, '2025-11-11 11:52:01', '2025-11-11 12:47:33', '2025-11-11 12:47:33');

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
(1, 2, 'employees', 'Employees', '', 'clipboard-list', 1, 1, 1, 'department', 'department', 'manager_only', '2025-11-10 13:12:24', '2025-11-10 13:12:24', 1),
(2, 3, 'machines', 'Machines', '', 'table', 1, 1, 1, 'department', 'department', 'manager_only', '2025-11-10 15:03:22', '2025-11-10 15:03:22', 1);

-- --------------------------------------------------------

--
-- Structure de la table `employee_requests`
--

CREATE TABLE `employee_requests` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `type` varchar(20) NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `loan_type` varchar(20) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `leave_type` varchar(20) DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `days` int(11) DEFAULT NULL,
  `permission_date` date DEFAULT NULL,
  `start_time` varchar(5) DEFAULT NULL,
  `end_time` varchar(5) DEFAULT NULL,
  `reason` text DEFAULT NULL,
  `approved_by_id` int(11) DEFAULT NULL,
  `expected_approver_id` int(11) DEFAULT NULL,
  `expected_approver_role` varchar(50) DEFAULT NULL,
  `blockchain_hash` varchar(64) DEFAULT NULL,
  `blockchain_block_index` int(11) DEFAULT NULL,
  `is_in_blockchain` tinyint(1) DEFAULT 0,
  `approved_at` datetime DEFAULT NULL,
  `admin_comment` text DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `employee_requests`
--

INSERT INTO `employee_requests` (`id`, `user_id`, `type`, `status`, `loan_type`, `amount`, `leave_type`, `start_date`, `end_date`, `days`, `permission_date`, `start_time`, `end_time`, `reason`, `approved_by_id`, `expected_approver_id`, `expected_approver_role`, `blockchain_hash`, `blockchain_block_index`, `is_in_blockchain`, `approved_at`, `admin_comment`, `created_at`, `updated_at`) VALUES
(1, 1, 'loan', 'rejected', 'salary', 1000.00, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'qsdcsqdc', 1, 1, 'admin', NULL, NULL, 0, '2025-11-11 08:11:27', 'qscqscqsc', '2025-11-11 08:11:11', '2025-11-11 08:11:27'),
(2, 1, 'leave', 'rejected', NULL, NULL, 'sick', '2025-11-11', '2025-11-11', 1, NULL, NULL, NULL, 'qscqscqsc', 1, 1, 'admin', NULL, NULL, 0, '2025-11-11 08:12:05', 'qsc', '2025-11-11 08:11:53', '2025-11-11 08:12:05'),
(3, 1, 'permission', 'rejected', NULL, NULL, NULL, NULL, NULL, NULL, '2025-11-11', '10:00', '11:00', 'qscqsc', 1, 1, 'admin', NULL, NULL, 0, '2025-11-11 08:12:36', 'qscqsc', '2025-11-11 08:12:29', '2025-11-11 08:12:36'),
(4, 3, 'loan', 'rejected', 'salary', 100.00, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'svdsdv', 1, 4, 'department_manager', NULL, NULL, 0, '2025-11-11 12:46:42', 'rdfv', '2025-11-11 08:14:27', '2025-11-11 12:46:42'),
(5, 1, 'loan', 'approved', 'salary', 150.00, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'dfvdfv', 1, 1, 'admin', NULL, NULL, 0, '2025-11-11 12:47:13', 'dfvdfvdfvdfv', '2025-11-11 12:47:02', '2025-11-11 12:47:13'),
(6, 1, 'leave', 'approved', NULL, NULL, 'paid', '2025-11-13', '2025-11-13', 1, NULL, NULL, NULL, 'aadazd', 1, 1, 'admin', '00009a9e625f65e46c79234fb52ab1edb2fb0fb1775e881c2c8dff1339c3ff0b', 1, 1, '2025-11-17 07:44:21', 'sdvsdv', '2025-11-13 07:41:26', '2025-11-17 07:44:24'),
(7, 2, 'leave', 'approved', NULL, NULL, 'paid', '2025-11-13', '2025-11-13', 1, NULL, NULL, NULL, 'csdcsdc', 1, 5, 'department_manager', '00008a18eda36a4f9e4043e98b54e8d09cd4fa56bca91cd4fa399c1a88cb87f3', 2, 1, '2025-11-17 07:45:01', 'sdvs', '2025-11-13 14:01:48', '2025-11-17 07:45:01'),
(8, 2, 'loan', 'approved', 'salary', 150.00, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'sdcs', 1, 5, 'department_manager', NULL, NULL, 0, '2025-11-13 14:08:00', 'sdcsdc', '2025-11-13 14:01:54', '2025-11-13 14:08:00');

-- --------------------------------------------------------

--
-- Structure de la table `employee_salaries`
--

CREATE TABLE `employee_salaries` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `base_salary` decimal(12,3) NOT NULL,
  `currency` varchar(3) DEFAULT NULL,
  `transport_allowance` decimal(10,3) DEFAULT NULL,
  `food_allowance` decimal(10,3) DEFAULT NULL,
  `housing_allowance` decimal(10,3) DEFAULT NULL,
  `responsibility_bonus` decimal(10,3) DEFAULT NULL,
  `payment_type` varchar(20) DEFAULT NULL,
  `hourly_rate` decimal(10,3) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `effective_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `employee_salaries`
--

INSERT INTO `employee_salaries` (`id`, `user_id`, `base_salary`, `currency`, `transport_allowance`, `food_allowance`, `housing_allowance`, `responsibility_bonus`, `payment_type`, `hourly_rate`, `is_active`, `effective_date`, `created_at`, `updated_at`) VALUES
(1, 3, 1000.000, 'TND', 50.000, 30.000, 50.000, 90.000, 'monthly', NULL, 1, '2025-11-13', '2025-11-13 07:38:51', '2025-11-13 07:38:51'),
(2, 2, 800.000, 'TND', 30.000, 20.000, 50.000, 60.000, 'monthly', NULL, 1, '2025-11-13', '2025-11-13 07:39:11', '2025-11-13 07:39:11'),
(3, 1, 1200.000, 'TND', 100.000, 60.000, 50.000, 120.000, 'monthly', NULL, 1, '2025-11-13', '2025-11-13 07:39:26', '2025-11-13 07:39:26'),
(4, 4, 1500.000, 'TND', 150.000, 100.000, 100.000, 150.000, 'monthly', NULL, 1, '2025-11-13', '2025-11-13 13:59:13', '2025-11-13 13:59:13');

-- --------------------------------------------------------

--
-- Structure de la table `leave_requests`
--

CREATE TABLE `leave_requests` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `leave_type` varchar(50) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `days_count` int(11) NOT NULL,
  `reason` text DEFAULT NULL,
  `attachment` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `reviewed_by_id` int(11) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_comment` text DEFAULT NULL,
  `is_paid` tinyint(1) DEFAULT NULL,
  `deduction_amount` decimal(10,3) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

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
(1, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, 'user_not_found', '2025-11-10 09:16:42'),
(2, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, 'user_not_found', '2025-11-10 09:16:44'),
(3, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, 'user_not_found', '2025-11-10 09:31:04'),
(4, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 09:34:54'),
(5, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 09:35:13'),
(6, 'test123', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 11:35:46'),
(7, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 11:36:18'),
(8, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 13:08:26'),
(9, 'testrh', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 13:14:50'),
(10, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-10 13:19:45'),
(11, 'Testrh', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-11 08:13:55'),
(12, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-11 08:14:40'),
(13, 'HammoudaAhmed', '192.168.218.92', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', 1, NULL, '2025-11-11 11:07:58'),
(14, 'HammoudaAhmed', '192.168.218.92', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', 1, NULL, '2025-11-11 11:11:49'),
(15, 'HammoudaAhmed', '192.168.213.43', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-11 14:22:09'),
(16, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-12 09:34:31'),
(17, 'HammoudaAhmed', '192.168.218.92', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', 1, NULL, '2025-11-12 14:00:55'),
(18, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 07:12:08'),
(19, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 07:42:02'),
(20, 'test123', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, 'invalid_password', '2025-11-13 12:33:30'),
(21, 'test123', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 12:33:38'),
(22, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 12:34:20'),
(23, 'test123', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 12:34:51'),
(24, 'manager', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 0, 'user_not_found', '2025-11-13 12:35:42'),
(25, 'testrh', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 12:35:53'),
(26, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 12:36:41'),
(27, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:13:55'),
(28, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:14:11'),
(29, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:14:21'),
(30, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:16:25'),
(31, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:18:14'),
(32, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 13:18:33'),
(33, 'test123', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 14:01:29'),
(34, 'MohamedAli', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 14:02:08'),
(35, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 14:02:55'),
(36, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-13 14:04:57'),
(37, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-17 07:11:14'),
(38, 'test123', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-17 15:09:19'),
(39, 'HammoudaAhmed', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', 1, NULL, '2025-11-17 15:09:57');

-- --------------------------------------------------------

--
-- Structure de la table `payslips`
--

CREATE TABLE `payslips` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `month` int(11) NOT NULL,
  `year` int(11) NOT NULL,
  `base_salary` decimal(12,3) NOT NULL,
  `transport_allowance` decimal(10,3) DEFAULT NULL,
  `food_allowance` decimal(10,3) DEFAULT NULL,
  `housing_allowance` decimal(10,3) DEFAULT NULL,
  `responsibility_bonus` decimal(10,3) DEFAULT NULL,
  `performance_bonus` decimal(10,3) DEFAULT NULL,
  `overtime_pay` decimal(10,3) DEFAULT NULL,
  `gross_salary` decimal(12,3) NOT NULL,
  `leave_deduction` decimal(10,3) DEFAULT NULL,
  `absence_deduction` decimal(10,3) DEFAULT NULL,
  `advance_deduction` decimal(10,3) DEFAULT NULL,
  `late_deduction` decimal(10,3) DEFAULT NULL,
  `cnss_employee` decimal(10,3) DEFAULT NULL,
  `cnss_employer` decimal(10,3) DEFAULT NULL,
  `irpp` decimal(10,3) DEFAULT NULL,
  `total_deductions` decimal(12,3) DEFAULT NULL,
  `net_salary` decimal(12,3) NOT NULL,
  `working_days` int(11) DEFAULT NULL,
  `days_worked` int(11) DEFAULT NULL,
  `leave_days` int(11) DEFAULT NULL,
  `absence_days` int(11) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `validated_by_id` int(11) DEFAULT NULL,
  `validated_at` datetime DEFAULT NULL,
  `paid_at` datetime DEFAULT NULL,
  `pdf_path` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `payslips`
--

INSERT INTO `payslips` (`id`, `user_id`, `month`, `year`, `base_salary`, `transport_allowance`, `food_allowance`, `housing_allowance`, `responsibility_bonus`, `performance_bonus`, `overtime_pay`, `gross_salary`, `leave_deduction`, `absence_deduction`, `advance_deduction`, `late_deduction`, `cnss_employee`, `cnss_employer`, `irpp`, `total_deductions`, `net_salary`, `working_days`, `days_worked`, `leave_days`, `absence_days`, `status`, `validated_by_id`, `validated_at`, `paid_at`, `pdf_path`, `created_at`, `updated_at`) VALUES
(1, 1, 11, 2025, 1200.000, 100.000, 60.000, 50.000, 120.000, 0.000, 0.000, 1530.000, 0.000, 0.000, 0.000, 0.000, 140.454, 253.521, 0.000, 140.454, 1389.546, 22, 22, 0, 0, 'validated', 1, '2025-11-13 14:08:16', NULL, 'payslips\\fiche_paie_HammoudaAhmed_2025_11.pdf', '2025-11-13 07:39:36', '2025-11-13 14:08:16'),
(2, 3, 2, 2025, 1000.000, 50.000, 30.000, 50.000, 90.000, 0.000, 0.000, 1220.000, 0.000, 0.000, 0.000, 0.000, 111.996, 202.154, 0.000, 111.996, 1108.004, 22, 22, 0, 0, 'validated', 1, '2025-11-13 07:45:41', NULL, NULL, '2025-11-13 07:45:32', '2025-11-13 07:45:41');

-- --------------------------------------------------------

--
-- Structure de la table `salary_advances`
--

CREATE TABLE `salary_advances` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `amount` decimal(10,3) NOT NULL,
  `currency` varchar(3) DEFAULT NULL,
  `reason` text DEFAULT NULL,
  `repayment_months` int(11) DEFAULT NULL,
  `monthly_deduction` decimal(10,3) DEFAULT NULL,
  `remaining_amount` decimal(10,3) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `approved_by_id` int(11) DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `request_date` datetime DEFAULT NULL,
  `disbursement_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Structure de la table `salary_configs`
--

CREATE TABLE `salary_configs` (
  `id` int(11) NOT NULL,
  `company_id` int(11) NOT NULL,
  `working_days_per_week` int(11) DEFAULT NULL,
  `working_hours_per_day` float DEFAULT NULL,
  `working_days_per_month` int(11) DEFAULT NULL,
  `cnss_rate` float DEFAULT NULL,
  `cnss_employer_rate` float DEFAULT NULL,
  `irpp_rate` float DEFAULT NULL,
  `annual_leave_days` int(11) DEFAULT NULL,
  `sick_leave_days` int(11) DEFAULT NULL,
  `absence_penalty_rate` float DEFAULT NULL,
  `late_penalty_rate` float DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `salary_configs`
--

INSERT INTO `salary_configs` (`id`, `company_id`, `working_days_per_week`, `working_hours_per_day`, `working_days_per_month`, `cnss_rate`, `cnss_employer_rate`, `irpp_rate`, `annual_leave_days`, `sick_leave_days`, `absence_penalty_rate`, `late_penalty_rate`, `created_at`, `updated_at`) VALUES
(1, 1, 5, 8, 22, 9.18, 16.57, 0, 30, 15, 100, 50, '2025-11-13 07:38:06', '2025-11-13 07:38:30');

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
(1, 1, 'sdvs', 'sdv', 'text', NULL, 0, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(2, 1, 'sdvs', 'dvsdv', 'text', NULL, 0, 0, NULL, NULL, 1, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(3, 1, 'sdv', 'sdv', 'text', NULL, 0, 0, NULL, NULL, 2, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(4, 1, 'hhnhnh', 'hnghg', 'text', NULL, 0, 0, NULL, NULL, 3, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(5, 1, 'fgnf', 'fgbfg', 'text', NULL, 0, 0, NULL, NULL, 4, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(6, 1, 'fgbfgb', 'fgbfg', 'text', NULL, 0, 0, NULL, NULL, 5, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 13:12:24'),
(7, 2, 'nom', 'Nom', 'text', NULL, 0, 0, NULL, NULL, 0, NULL, 1, 1, 1, NULL, NULL, NULL, '2025-11-10 15:03:22');

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
(1, 1, '{\"sdvs\": \"dfvdfvfffff\", \"sdv\": \"sdcsd\", \"hhnhnh\": \"csdc\", \"fgnf\": \"sdcs\", \"fgbfgb\": \"125\"}', 0, 1, '2025-11-10 13:12:54', '2025-11-10 13:15:19', 1, 3),
(2, 1, '{\"sdvs\": \"svdsfvdfvd\", \"sdv\": \"vdfvdfv\", \"hhnhnh\": \"dfvdf\", \"fgnf\": \"vdfvdfv\", \"fgbfgb\": \"dfvdfv\"}', 0, 1, '2025-11-10 13:15:08', '2025-11-10 13:15:13', 3, 3),
(3, 2, '{\"nom\": \"bdfb\"}', 0, 1, '2025-11-13 14:02:28', '2025-11-13 14:02:28', 5, NULL);

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
  `can_read` tinyint(1) NOT NULL DEFAULT 1,
  `can_write` tinyint(1) NOT NULL DEFAULT 0,
  `can_create` tinyint(1) NOT NULL DEFAULT 0,
  `can_update` tinyint(1) NOT NULL DEFAULT 0,
  `can_delete` tinyint(1) NOT NULL DEFAULT 0,
  `can_add_tables` tinyint(1) NOT NULL DEFAULT 0,
  `can_add_columns` tinyint(1) NOT NULL DEFAULT 0,
  `can_access_payroll` tinyint(1) DEFAULT 0,
  `can_manage_users` tinyint(1) DEFAULT 0,
  `can_delete_users` tinyint(1) DEFAULT 0,
  `can_approve_leaves` tinyint(1) DEFAULT 0,
  `can_approve_advances` tinyint(1) DEFAULT 0,
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
  `department_id` int(11) DEFAULT NULL,
  `is_online` tinyint(1) DEFAULT 0,
  `last_seen` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Déchargement des données de la table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `first_name`, `last_name`, `phone`, `is_admin`, `is_active`, `role`, `can_read`, `can_write`, `can_create`, `can_update`, `can_delete`, `can_add_tables`, `can_add_columns`, `can_access_payroll`, `can_manage_users`, `can_delete_users`, `can_approve_leaves`, `can_approve_advances`, `failed_login_attempts`, `account_locked_until`, `password_changed_at`, `two_factor_enabled`, `two_factor_secret`, `created_at`, `updated_at`, `last_login`, `last_ip`, `company_id`, `department_id`, `is_online`, `last_seen`) VALUES
(1, 'HammoudaAhmed', 'ahmedmustapha.hammouda@gmail.com', 'pbkdf2:sha256:600000$eK6G8sUmKTYJokNU$9bd2682b9968c9b591b20999394ab09a4e0da64ab4a01efc7cb0707a00683f11', 'Ahmed', 'Hammouda', '12345678', 1, 1, 'admin', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, NULL, '2025-11-10 09:34:54', 0, NULL, '2025-11-10 09:34:54', '2025-11-17 15:10:14', '2025-11-17 15:09:57', '127.0.0.1', 1, NULL, 1, '2025-11-17 15:10:14'),
(2, 'test123', 'test.123@gmail.com', 'pbkdf2:sha256:600000$B8V9A1M9RAV1oWXX$cd9442aba8b2acae2556055f725f053600183014d8b70796a26ba08d344cd974', 'test', 'test', '12345678', 0, 1, 'technician', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, NULL, '2025-11-10 11:35:15', 0, NULL, '2025-11-10 11:35:15', '2025-11-17 15:11:12', '2025-11-17 15:09:19', '127.0.0.1', 1, 3, 0, '2025-11-17 15:11:12'),
(3, 'testrh', 'testrh@gmail.com', 'pbkdf2:sha256:600000$JIiBHnWhwOylFGGd$59ab5c395dfe2c0800a14da7a21cc710ad13d945cb831a3f27e06ce6e1c3a528', 'test', 'rh', '12345678', 0, 1, 'employee', 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, NULL, '2025-11-10 13:14:33', 0, NULL, '2025-11-10 13:14:33', '2025-11-13 12:35:53', '2025-11-13 12:35:53', '127.0.0.1', 1, 2, 0, '2025-11-17 10:32:10'),
(4, 'directeur_rh', 'drh@company.com', 'your_password_hash', 'Directeur', 'RH', '12345678', 0, 1, 'department_manager', 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, NULL, NULL, NULL, NULL, NULL, '2025-11-13 14:53:00', '2025-11-17 07:12:07', NULL, NULL, 1, 2, 0, '2025-11-17 10:32:10'),
(5, 'MohamedAli', 'test@gmail.com', 'pbkdf2:sha256:600000$mD4WEPuSHYob7bWT$8dbe778e1b3ed28b8853e56dd589e91bcce89e169e3a705348cc9d043a62f283', 'mohamed', 'ali', '12345678', 0, 1, 'department_manager', 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, NULL, '2025-11-13 14:00:35', 0, NULL, '2025-11-13 14:00:35', '2025-11-13 14:02:08', '2025-11-13 14:02:08', '127.0.0.1', 1, 3, 0, '2025-11-17 10:32:10');

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `v_employee_requests_hierarchy`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `v_employee_requests_hierarchy` (
`id` int(11)
,`type` varchar(20)
,`status` varchar(20)
,`created_at` datetime
,`requester_id` int(11)
,`requester_username` varchar(80)
,`requester_name` varchar(201)
,`requester_role` varchar(50)
,`requester_department` varchar(100)
,`expected_approver_id` int(11)
,`expected_approver_username` varchar(80)
,`expected_approver_name` varchar(201)
,`expected_approver_role` varchar(50)
,`actual_approver_id` int(11)
,`actual_approver_username` varchar(80)
,`actual_approver_name` varchar(201)
,`actual_approver_role` varchar(50)
,`approved_at` datetime
,`blockchain_hash` varchar(64)
,`blockchain_block_index` int(11)
,`is_in_blockchain` tinyint(1)
,`leave_type` varchar(20)
,`start_date` date
,`end_date` date
,`days` int(11)
,`amount` decimal(10,2)
,`reason` text
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `v_pending_requests_by_approver`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `v_pending_requests_by_approver` (
`approver_id` int(11)
,`approver_username` varchar(80)
,`approver_name` varchar(201)
,`approver_role` varchar(50)
,`pending_count` bigint(21)
,`pending_requests` mediumtext
);

-- --------------------------------------------------------

--
-- Structure de la vue `v_employee_requests_hierarchy`
--
DROP TABLE IF EXISTS `v_employee_requests_hierarchy`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_employee_requests_hierarchy`  AS SELECT `er`.`id` AS `id`, `er`.`type` AS `type`, `er`.`status` AS `status`, `er`.`created_at` AS `created_at`, `u`.`id` AS `requester_id`, `u`.`username` AS `requester_username`, concat(`u`.`first_name`,' ',`u`.`last_name`) AS `requester_name`, `u`.`role` AS `requester_role`, `d`.`name` AS `requester_department`, `ea`.`id` AS `expected_approver_id`, `ea`.`username` AS `expected_approver_username`, concat(`ea`.`first_name`,' ',`ea`.`last_name`) AS `expected_approver_name`, `er`.`expected_approver_role` AS `expected_approver_role`, `aa`.`id` AS `actual_approver_id`, `aa`.`username` AS `actual_approver_username`, concat(`aa`.`first_name`,' ',`aa`.`last_name`) AS `actual_approver_name`, `aa`.`role` AS `actual_approver_role`, `er`.`approved_at` AS `approved_at`, `er`.`blockchain_hash` AS `blockchain_hash`, `er`.`blockchain_block_index` AS `blockchain_block_index`, `er`.`is_in_blockchain` AS `is_in_blockchain`, `er`.`leave_type` AS `leave_type`, `er`.`start_date` AS `start_date`, `er`.`end_date` AS `end_date`, `er`.`days` AS `days`, `er`.`amount` AS `amount`, `er`.`reason` AS `reason` FROM ((((`employee_requests` `er` join `users` `u` on(`er`.`user_id` = `u`.`id`)) left join `departments` `d` on(`u`.`department_id` = `d`.`id`)) left join `users` `ea` on(`er`.`expected_approver_id` = `ea`.`id`)) left join `users` `aa` on(`er`.`approved_by_id` = `aa`.`id`)) ;

-- --------------------------------------------------------

--
-- Structure de la vue `v_pending_requests_by_approver`
--
DROP TABLE IF EXISTS `v_pending_requests_by_approver`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_pending_requests_by_approver`  AS SELECT `ea`.`id` AS `approver_id`, `ea`.`username` AS `approver_username`, concat(`ea`.`first_name`,' ',`ea`.`last_name`) AS `approver_name`, `ea`.`role` AS `approver_role`, count(0) AS `pending_count`, group_concat(concat(`u`.`first_name`,' ',`u`.`last_name`,' (',`er`.`type`,')') separator ', ') AS `pending_requests` FROM ((`employee_requests` `er` join `users` `u` on(`er`.`user_id` = `u`.`id`)) join `users` `ea` on(`er`.`expected_approver_id` = `ea`.`id`)) WHERE `er`.`status` = 'pending' GROUP BY `ea`.`id`, `ea`.`username`, `ea`.`first_name`, `ea`.`last_name`, `ea`.`role` ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `attendances`
--
ALTER TABLE `attendances`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_user_date` (`user_id`,`date`);

--
-- Index pour la table `chat_conversations`
--
ALTER TABLE `chat_conversations`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_conversation` (`user1_id`,`user2_id`),
  ADD KEY `user2_id` (`user2_id`),
  ADD KEY `idx_conv_users` (`user1_id`,`user2_id`);

--
-- Index pour la table `chat_files`
--
ALTER TABLE `chat_files`
  ADD PRIMARY KEY (`id`),
  ADD KEY `conversation_id` (`conversation_id`),
  ADD KEY `group_id` (`group_id`),
  ADD KEY `uploaded_by_id` (`uploaded_by_id`);

--
-- Index pour la table `chat_groups`
--
ALTER TABLE `chat_groups`
  ADD PRIMARY KEY (`id`),
  ADD KEY `created_by_id` (`created_by_id`);

--
-- Index pour la table `chat_group_members`
--
ALTER TABLE `chat_group_members`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_group_member` (`group_id`,`user_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_group_user` (`group_id`,`user_id`);

--
-- Index pour la table `chat_messages`
--
ALTER TABLE `chat_messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `sender_id` (`sender_id`),
  ADD KEY `file_id` (`file_id`),
  ADD KEY `reply_to_id` (`reply_to_id`),
  ADD KEY `idx_conv_messages` (`conversation_id`,`created_at`),
  ADD KEY `ix_chat_messages_created_at` (`created_at`),
  ADD KEY `idx_group_messages` (`group_id`,`created_at`);

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
  ADD KEY `parent_id` (`parent_id`),
  ADD KEY `company_id` (`company_id`);

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
  ADD KEY `updated_by_id` (`updated_by_id`),
  ADD KEY `idx_dept_item_type` (`department_id`,`item_type`);

--
-- Index pour la table `department_tables`
--
ALTER TABLE `department_tables`
  ADD PRIMARY KEY (`id`),
  ADD KEY `department_id` (`department_id`),
  ADD KEY `created_by_id` (`created_by_id`);

--
-- Index pour la table `employee_requests`
--
ALTER TABLE `employee_requests`
  ADD PRIMARY KEY (`id`),
  ADD KEY `approved_by_id` (`approved_by_id`),
  ADD KEY `idx_user_status` (`user_id`,`status`),
  ADD KEY `idx_type_status` (`type`,`status`),
  ADD KEY `idx_created_at` (`created_at`),
  ADD KEY `idx_expected_approver_status` (`expected_approver_id`,`status`),
  ADD KEY `idx_blockchain` (`is_in_blockchain`);

--
-- Index pour la table `employee_salaries`
--
ALTER TABLE `employee_salaries`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Index pour la table `leave_requests`
--
ALTER TABLE `leave_requests`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `reviewed_by_id` (`reviewed_by_id`);

--
-- Index pour la table `login_attempts`
--
ALTER TABLE `login_attempts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_login_attempts_username` (`username`),
  ADD KEY `ix_login_attempts_timestamp` (`timestamp`);

--
-- Index pour la table `payslips`
--
ALTER TABLE `payslips`
  ADD PRIMARY KEY (`id`),
  ADD KEY `validated_by_id` (`validated_by_id`),
  ADD KEY `idx_user_period` (`user_id`,`year`,`month`);

--
-- Index pour la table `salary_advances`
--
ALTER TABLE `salary_advances`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `approved_by_id` (`approved_by_id`);

--
-- Index pour la table `salary_configs`
--
ALTER TABLE `salary_configs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `company_id` (`company_id`);

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
-- AUTO_INCREMENT pour la table `attendances`
--
ALTER TABLE `attendances`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `chat_conversations`
--
ALTER TABLE `chat_conversations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT pour la table `chat_files`
--
ALTER TABLE `chat_files`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `chat_groups`
--
ALTER TABLE `chat_groups`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `chat_group_members`
--
ALTER TABLE `chat_group_members`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `chat_messages`
--
ALTER TABLE `chat_messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT pour la table `companies`
--
ALTER TABLE `companies`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `employee_requests`
--
ALTER TABLE `employee_requests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT pour la table `employee_salaries`
--
ALTER TABLE `employee_salaries`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT pour la table `leave_requests`
--
ALTER TABLE `leave_requests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `login_attempts`
--
ALTER TABLE `login_attempts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=40;

--
-- AUTO_INCREMENT pour la table `payslips`
--
ALTER TABLE `payslips`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT pour la table `salary_advances`
--
ALTER TABLE `salary_advances`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `salary_configs`
--
ALTER TABLE `salary_configs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT pour la table `sessions`
--
ALTER TABLE `sessions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT pour la table `table_columns`
--
ALTER TABLE `table_columns`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- Contraintes pour les tables déchargées
--

--
-- Contraintes pour la table `attendances`
--
ALTER TABLE `attendances`
  ADD CONSTRAINT `attendances_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `chat_conversations`
--
ALTER TABLE `chat_conversations`
  ADD CONSTRAINT `chat_conversations_ibfk_1` FOREIGN KEY (`user1_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `chat_conversations_ibfk_2` FOREIGN KEY (`user2_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `chat_files`
--
ALTER TABLE `chat_files`
  ADD CONSTRAINT `chat_files_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversations` (`id`),
  ADD CONSTRAINT `chat_files_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `chat_groups` (`id`),
  ADD CONSTRAINT `chat_files_ibfk_3` FOREIGN KEY (`uploaded_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `chat_groups`
--
ALTER TABLE `chat_groups`
  ADD CONSTRAINT `chat_groups_ibfk_1` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `chat_group_members`
--
ALTER TABLE `chat_group_members`
  ADD CONSTRAINT `chat_group_members_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `chat_groups` (`id`),
  ADD CONSTRAINT `chat_group_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `chat_messages`
--
ALTER TABLE `chat_messages`
  ADD CONSTRAINT `chat_messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversations` (`id`),
  ADD CONSTRAINT `chat_messages_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `chat_groups` (`id`),
  ADD CONSTRAINT `chat_messages_ibfk_3` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `chat_messages_ibfk_4` FOREIGN KEY (`file_id`) REFERENCES `chat_files` (`id`),
  ADD CONSTRAINT `chat_messages_ibfk_5` FOREIGN KEY (`reply_to_id`) REFERENCES `chat_messages` (`id`);

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
  ADD CONSTRAINT `departments_ibfk_2` FOREIGN KEY (`parent_id`) REFERENCES `departments` (`id`),
  ADD CONSTRAINT `departments_ibfk_3` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`);

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
  ADD CONSTRAINT `department_items_ibfk_3` FOREIGN KEY (`updated_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `department_tables`
--
ALTER TABLE `department_tables`
  ADD CONSTRAINT `department_tables_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  ADD CONSTRAINT `department_tables_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `employee_requests`
--
ALTER TABLE `employee_requests`
  ADD CONSTRAINT `employee_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `employee_requests_ibfk_2` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `fk_employee_requests_expected_approver` FOREIGN KEY (`expected_approver_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Contraintes pour la table `employee_salaries`
--
ALTER TABLE `employee_salaries`
  ADD CONSTRAINT `employee_salaries_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `leave_requests`
--
ALTER TABLE `leave_requests`
  ADD CONSTRAINT `leave_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `leave_requests_ibfk_2` FOREIGN KEY (`reviewed_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `payslips`
--
ALTER TABLE `payslips`
  ADD CONSTRAINT `payslips_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `payslips_ibfk_2` FOREIGN KEY (`validated_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `salary_advances`
--
ALTER TABLE `salary_advances`
  ADD CONSTRAINT `salary_advances_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `salary_advances_ibfk_2` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`);

--
-- Contraintes pour la table `salary_configs`
--
ALTER TABLE `salary_configs`
  ADD CONSTRAINT `salary_configs_ibfk_1` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`);

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
