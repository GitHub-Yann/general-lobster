-- Doc Analyzer MySQL Schema
-- 说明：
-- 1) 适用于 MySQL 8.0+
-- 2) 编码统一 utf8mb4
-- 3) 包含现有表 + LLM 精修扩展结构

CREATE DATABASE IF NOT EXISTS `doc_analyzer`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `doc_analyzer`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =========================================================
-- 1) 核心任务表
-- =========================================================
CREATE TABLE IF NOT EXISTS `tasks` (
  `task_id` VARCHAR(36) NOT NULL,
  `filename` VARCHAR(255) NOT NULL,
  `file_path` VARCHAR(500) NOT NULL,
  `file_type` VARCHAR(20) NULL COMMENT 'pdf, docx, txt, url',
  `config_name` VARCHAR(50) NOT NULL DEFAULT 'default',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, running, completed, failed',
  `current_node` VARCHAR(50) NOT NULL DEFAULT 'upload',
  `result_data` LONGTEXT NULL COMMENT '最终结果 JSON',
  `domain_keywords` LONGTEXT NULL COMMENT '用户输入领域词（原始字符串或JSON）',
  `noise_words` LONGTEXT NULL COMMENT '用户输入噪音词（原始字符串或JSON）',
  -- LLM 精修扩展（可选）
  `use_llm_refine` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否启用LLM精修',
  `llm_config_id` INT NULL COMMENT '关联 llm_configs.id',
  `prompt_template_id` INT NULL COMMENT '关联 llm_prompt_templates.id',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  INDEX `idx_tasks_status_created` (`status`, `created_at`),
  INDEX `idx_tasks_current_node` (`current_node`),
  INDEX `idx_tasks_llm_config_id` (`llm_config_id`),
  INDEX `idx_tasks_prompt_template_id` (`prompt_template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 2) 节点配置表
-- =========================================================
CREATE TABLE IF NOT EXISTS `node_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `config_name` VARCHAR(50) NOT NULL,
  `nodes` LONGTEXT NOT NULL COMMENT '节点数组 JSON',
  `description` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_node_configs_config_name` (`config_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 3) 节点运行数据表
-- =========================================================
CREATE TABLE IF NOT EXISTS `node_data` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `task_id` VARCHAR(36) NOT NULL,
  `node_name` VARCHAR(50) NOT NULL COMMENT 'upload, parse, segment, keyword, summary, output, llm_refine',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, running, completed, failed',
  `input_data` LONGTEXT NULL COMMENT '输入 JSON',
  `output_data` LONGTEXT NULL COMMENT '输出 JSON',
  `error_msg` LONGTEXT NULL,
  `started_at` DATETIME NULL,
  `completed_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uix_task_node` (`task_id`, `node_name`),
  INDEX `idx_node_data_task_status` (`task_id`, `status`),
  CONSTRAINT `fk_node_data_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 4) LLM 配置表（可配置供应商、模型、地址、密钥）
-- =========================================================
CREATE TABLE IF NOT EXISTS `llm_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `provider` VARCHAR(50) NOT NULL COMMENT 'openai, claude, wenxin ...',
  `name` VARCHAR(100) NOT NULL COMMENT '配置名称',
  `api_key` LONGTEXT NULL COMMENT '建议应用层加密后存储',
  `api_base` VARCHAR(500) NULL,
  `model` VARCHAR(100) NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 0,
  `config` LONGTEXT NULL COMMENT '额外参数 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_llm_configs_name` (`name`),
  INDEX `idx_llm_configs_provider_enabled` (`provider`, `enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 5) Prompt 模板表（系统提示词可配置）
-- =========================================================
CREATE TABLE IF NOT EXISTS `llm_prompt_templates` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `scene` VARCHAR(50) NOT NULL COMMENT 'keyword_refine, summary_refine, doc_refine',
  `version` VARCHAR(30) NOT NULL DEFAULT 'v1',
  `system_prompt` LONGTEXT NOT NULL,
  `user_prompt_template` LONGTEXT NOT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prompt_name_scene_version` (`name`, `scene`, `version`),
  INDEX `idx_prompt_scene_enabled` (`scene`, `enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 6) LLM 调用日志表（可追踪/审计）
-- =========================================================
CREATE TABLE IF NOT EXISTS `llm_call_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` VARCHAR(36) NULL,
  `provider` VARCHAR(50) NOT NULL,
  `model` VARCHAR(100) NULL,
  `prompt_template_id` INT NULL,
  `request_payload` LONGTEXT NULL COMMENT '请求体（建议脱敏后存储）',
  `response_payload` LONGTEXT NULL COMMENT '响应体（建议脱敏后存储）',
  `success` TINYINT(1) NOT NULL DEFAULT 0,
  `error_message` TEXT NULL,
  `latency_ms` INT NULL,
  `token_in` INT NULL,
  `token_out` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_llm_call_logs_task_time` (`task_id`, `created_at`),
  INDEX `idx_llm_call_logs_provider_time` (`provider`, `created_at`),
  CONSTRAINT `fk_llm_call_logs_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_llm_call_logs_prompt_template_id`
    FOREIGN KEY (`prompt_template_id`) REFERENCES `llm_prompt_templates` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 7) 外键补充（tasks 关联 llm_configs / prompt templates，幂等）
-- =========================================================
SET @fk_exists := (
  SELECT COUNT(1)
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND CONSTRAINT_NAME = 'fk_tasks_llm_config_id'
    AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);
SET @sql := IF(
  @fk_exists = 0,
  'ALTER TABLE `tasks` ADD CONSTRAINT `fk_tasks_llm_config_id` FOREIGN KEY (`llm_config_id`) REFERENCES `llm_configs` (`id`) ON DELETE SET NULL ON UPDATE CASCADE',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists := (
  SELECT COUNT(1)
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tasks'
    AND CONSTRAINT_NAME = 'fk_tasks_prompt_template_id'
    AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);
SET @sql := IF(
  @fk_exists = 0,
  'ALTER TABLE `tasks` ADD CONSTRAINT `fk_tasks_prompt_template_id` FOREIGN KEY (`prompt_template_id`) REFERENCES `llm_prompt_templates` (`id`) ON DELETE SET NULL ON UPDATE CASCADE',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =========================================================
-- 8) 初始化默认节点配置（幂等）
-- =========================================================
INSERT INTO `node_configs` (`config_name`, `nodes`, `description`)
VALUES
  ('default', '["upload","parse","segment","keyword","summary","output"]', '默认完整流程，适用于 PDF/DOCX'),
  ('txt_only', '["upload","segment","keyword","summary","output"]', 'TXT 文件流程，跳过解析节点'),
  ('keyword_only', '["upload","parse","keyword","output"]', '仅提取关键词，快速模式')
ON DUPLICATE KEY UPDATE
  `nodes` = VALUES(`nodes`),
  `description` = VALUES(`description`);

SET FOREIGN_KEY_CHECKS = 1;
