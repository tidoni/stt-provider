DROP TABLE IF EXISTS `stt_tasks`;

CREATE TABLE `stt_tasks` (
  `task_id` int(11) NOT NULL AUTO_INCREMENT,
  `file_path` varchar(511) DEFAULT NULL,
  `callback_url` varchar(511) DEFAULT NULL,
  `processing_started` tinyint(4) DEFAULT '0',
  `callback_send` tinyint(4) DEFAULT '0',
  `error_encountered` tinyint(4) DEFAULT '0',
  `result_text` longtext,
  `segments_json` longtext,
  `download_url` varchar(255) DEFAULT '',
  `file_name` varchar(255) DEFAULT '',
  `pit_task_added` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `pit_processing_started` timestamp NULL DEFAULT NULL,
  `pit_processing_finished` timestamp NULL DEFAULT NULL,
  `initial_prompt` varchar(4096) DEFAULT '',
  `duration_in_seconds` int(11) DEFAULT NULL,
  PRIMARY KEY (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
