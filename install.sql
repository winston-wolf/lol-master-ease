-- MySQL dump 10.13  Distrib 5.6.23, for Win64 (x86_64)
--
-- Host: localhost    Database: lol_master_ease
-- ------------------------------------------------------
-- Server version	5.5.5-10.0.19-MariaDB-1~trusty

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `aggregate_freelo_deviations`
--

DROP TABLE IF EXISTS `aggregate_freelo_deviations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `aggregate_freelo_deviations` (
  `champion_role` varchar(20) NOT NULL,
  `champion_id` int(11) NOT NULL,
  `games_on_record` int(11) NOT NULL,
  `freelo_dev_cs` int(10) NOT NULL,
  `average_cs` int(10) NOT NULL,
  `freelo_dev_vision_wards_placed` int(10) NOT NULL,
  `average_vision_wards_placed` int(10) NOT NULL,
  `freelo_dev_assists` int(10) NOT NULL,
  `average_assists` int(10) NOT NULL,
  `freelo_dev_deaths` int(10) NOT NULL,
  `average_deaths` int(10) NOT NULL,
  `freelo_dev_kills` int(10) NOT NULL,
  `average_kills` int(10) NOT NULL,
  `freelo_dev_sight_wards_placed` int(10) NOT NULL,
  `average_sight_wards_placed` int(10) NOT NULL,
  `freelo_dev_first_dragon_time_in_minutes` int(10) NOT NULL,
  `average_cs_first_dragon_time_in_minutes` int(10) NOT NULL,
  `freelo_dev_match_time_in_minutes` int(10) NOT NULL,
  `average_match_time_in_minutes` int(10) NOT NULL,
  `freelo_dev_damage_done_to_champions` int(10) NOT NULL,
  `average_damage_done_to_champions` int(10) NOT NULL,
  PRIMARY KEY (`champion_role`,`champion_id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `champions`
--

DROP TABLE IF EXISTS `champions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `champions` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `image_icon_url` varchar(300) NOT NULL,
  `image_loading_url` varchar(300) NOT NULL,
  `image_splash_url` varchar(300) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `items`
--

DROP TABLE IF EXISTS `items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `items` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `image_icon_url` varchar(300) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `match_frame_delta_vs_enemy_laner`
--

DROP TABLE IF EXISTS `match_frame_delta_vs_enemy_laner`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `match_frame_delta_vs_enemy_laner` (
  `match_id` bigint(20) NOT NULL,
  `match_region` enum('br','eune','euw','kr','lan','las','na','oce','ru','tr') NOT NULL,
  `summoner_id` bigint(20) NOT NULL,
  `frame_start_minutes` smallint(6) NOT NULL,
  `frame_end_minutes` smallint(6) NOT NULL,
  `creeps_per_minute` float NOT NULL,
  `xp_per_minute` float NOT NULL,
  `damage_taken_per_minute` float NOT NULL,
  PRIMARY KEY (`match_id`,`match_region`,`summoner_id`,`frame_start_minutes`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `match_frames`
--

DROP TABLE IF EXISTS `match_frames`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `match_frames` (
  `match_id` bigint(20) NOT NULL,
  `match_region` enum('br','eune','euw','kr','lan','las','na','oce','ru','tr') NOT NULL,
  `summoner_id` bigint(20) NOT NULL,
  `frame_start_time_in_minutes` smallint(6) NOT NULL,
  `xp_earned_total` mediumint(9) NOT NULL,
  `gold_earned_total` mediumint(9) NOT NULL,
  `gold_unused` mediumint(9) NOT NULL,
  `deaths_total` smallint(6) NOT NULL,
  `deaths_this_frame` smallint(6) NOT NULL,
  `assists_total` smallint(6) NOT NULL,
  `assists_this_frame` smallint(6) NOT NULL,
  `kills_total` smallint(6) NOT NULL,
  `kills_this_frame` smallint(6) NOT NULL,
  `minion_kills_total` smallint(6) NOT NULL,
  `jungle_minion_kills_total` smallint(6) NOT NULL,
  `vision_wards_placed_this_frame` smallint(6) NOT NULL,
  `vision_wards_placed_total` smallint(6) NOT NULL,
  `sight_wards_placed_this_frame` smallint(6) NOT NULL,
  `sight_wards_placed_total` smallint(6) NOT NULL,
  PRIMARY KEY (`match_id`,`match_region`,`summoner_id`,`frame_start_time_in_minutes`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `matches`
--

DROP TABLE IF EXISTS `matches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `matches` (
  `match_id` bigint(20) NOT NULL,
  `match_region` enum('br','eune','euw','kr','lan','las','na','oce','ru','tr') NOT NULL,
  `summoner_id` bigint(20) NOT NULL,
  `summoner_rank_tier` enum('UNRANKED','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','MASTER','CHALLENGER') NOT NULL,
  `summoner_rank_division` varchar(5) DEFAULT NULL,
  `match_season` varchar(15) NOT NULL,
  `match_queue_type` varchar(15) NOT NULL,
  `match_create_datetime` datetime NOT NULL,
  `match_total_time_in_minutes` int(11) NOT NULL,
  `summoner_role` varchar(20) NOT NULL,
  `summoner_lane` varchar(20) NOT NULL,
  `summoner_champion_id` mediumint(9) NOT NULL,
  `summoner_champion_level` smallint(6) NOT NULL,
  `summoner_spell_1_id` mediumint(9) NOT NULL,
  `summoner_spell_2_id` mediumint(9) NOT NULL,
  `summoner_item_0_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_1_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_2_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_3_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_4_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_5_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_item_6_id` mediumint(9) NOT NULL DEFAULT '0',
  `summoner_is_winner` tinyint(1) NOT NULL,
  `summoner_team_id` smallint(6) NOT NULL,
  `summoner_kills_total` smallint(6) NOT NULL,
  `summoner_kills_double` smallint(6) NOT NULL,
  `summoner_kills_triple` smallint(6) NOT NULL,
  `summoner_kills_quadra` smallint(6) NOT NULL,
  `summoner_kills_penta` smallint(6) NOT NULL,
  `summoner_killing_sprees` smallint(6) NOT NULL,
  `summoner_deaths` smallint(6) NOT NULL,
  `summoner_assists` smallint(6) NOT NULL,
  `team_first_dragon_kill_time_in_minutes` smallint(6) DEFAULT NULL,
  `team_killed_first_dragon` tinyint(1) NOT NULL,
  `team_killed_first_baron` tinyint(1) NOT NULL,
  `team_killed_first_tower` tinyint(1) NOT NULL,
  `team_killed_first_inhibitor` tinyint(1) NOT NULL,
  `team_killed_first_champion` tinyint(1) NOT NULL,
  `team_dragon_kills` smallint(6) NOT NULL,
  `team_baron_kills` smallint(6) NOT NULL,
  `team_sight_wards_placed` smallint(6) NOT NULL,
  `team_vision_wards_placed` smallint(6) NOT NULL,
  `summoner_inhibitor_kills` smallint(6) NOT NULL,
  `summoner_tower_kills` smallint(6) NOT NULL,
  `summoner_tower_kills_in_lane` smallint(6) NOT NULL,
  `summoner_sight_wards_purchased` smallint(6) NOT NULL,
  `summoner_sight_wards_placed` smallint(6) NOT NULL,
  `summoner_sight_wards_killed` smallint(6) NOT NULL,
  `summoner_vision_wards_purchased` smallint(6) NOT NULL,
  `summoner_vision_wards_placed` smallint(6) NOT NULL,
  `summoner_vision_wards_killed` smallint(6) NOT NULL,
  `summoner_damage_done_to_champions` mediumint(9) NOT NULL,
  `summoner_damage_taken` mediumint(9) NOT NULL,
  `summoner_xp_earned` mediumint(9) NOT NULL,
  `summoner_minions_killed` smallint(6) NOT NULL,
  `summoner_neutral_minions_killed_enemy_jungle` smallint(6) NOT NULL,
  `summoner_neutral_minions_killed_team_jungle` smallint(6) NOT NULL,
  `summoner_healing_done_total` mediumint(9) NOT NULL,
  `summoner_gold_spent` mediumint(9) NOT NULL,
  `summoner_gold_earned` mediumint(9) NOT NULL,
  `summoner_crowd_control_time_dealt_in_seconds` float NOT NULL,
  `summoner_trinket_upgraded` tinyint(1) NOT NULL,
  `details_pulled` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`match_id`,`match_region`,`summoner_id`),
  KEY `summoner_rank_tier` (`summoner_rank_tier`,`summoner_role`,`summoner_lane`,`summoner_champion_id`),
  KEY `match_region` (`match_region`,`summoner_id`,`match_create_datetime`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `summoner_spells`
--

DROP TABLE IF EXISTS `summoner_spells`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `summoner_spells` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `image_icon_url` varchar(300) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `summoners`
--

DROP TABLE IF EXISTS `summoners`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `summoners` (
  `id` bigint(20) NOT NULL,
  `region` enum('br','eune','euw','kr','lan','las','na','oce','ru','tr') NOT NULL,
  `platform` varchar(10) NOT NULL DEFAULT 'NA1',
  `name` varchar(20) NOT NULL,
  `searchable_name` varchar(20) NOT NULL,
  `rank_tier` enum('UNRANKED','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','MASTER','CHALLENGER') NOT NULL,
  `rank_division` varchar(5) DEFAULT NULL,
  `last_spider_datetime` datetime DEFAULT NULL,
  `last_refresh_datetime` datetime DEFAULT NULL,
  `last_update_datetime` datetime NOT NULL,
  PRIMARY KEY (`id`,`region`),
  KEY `last_spider_datetime` (`last_spider_datetime`,`rank_tier`),
  KEY `region` (`searchable_name`,`region`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8 `compression`='tokudb_zlib';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-06-07 16:19:42

