CREATE DATABASE  IF NOT EXISTS `stock_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `stock_db`;
-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: stock_db
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Drop tables in reverse dependency order
--

DROP TABLE IF EXISTS `inventory_update_item`;
DROP TABLE IF EXISTS `purchase_order_item`;
DROP TABLE IF EXISTS `inventory_update`;
DROP TABLE IF EXISTS `sale`;
DROP TABLE IF EXISTS `job_instance`;
DROP TABLE IF EXISTS `job_consumables`;
DROP TABLE IF EXISTS `product_supplier`;
DROP TABLE IF EXISTS `purchase_order`;
DROP TABLE IF EXISTS `user`;
DROP TABLE IF EXISTS `job`;
DROP TABLE IF EXISTS `product`;
DROP TABLE IF EXISTS `supplier`;

--
-- Table structure for table `supplier`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `supplier` (
  `supplier_id` int NOT NULL AUTO_INCREMENT,
  `supplier_name` varchar(255) NOT NULL,
  `supplier_from_date` date NOT NULL DEFAULT (curdate()),
  `reason_for_changing_supplier` text,
  PRIMARY KEY (`supplier_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product` (
  `product_id` int NOT NULL AUTO_INCREMENT,
  `product_name` varchar(255) NOT NULL,
  `product_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `product_holding_cost` decimal(10,2) NOT NULL DEFAULT '0.00',
  `stock_quantity` int NOT NULL DEFAULT '0',
  `reserved_quantity` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job` (
  `job_id` int NOT NULL AUTO_INCREMENT,
  `job_name` varchar(255) NOT NULL,
  `job_description` text,
  PRIMARY KEY (`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL DEFAULT '1234',
  `password_change` enum('True','False') NOT NULL DEFAULT 'False',
  `password_change_request` enum('True','False') NOT NULL DEFAULT 'False',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `purchase_order`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_order` (
  `order_id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `order_date` date NOT NULL DEFAULT (curdate()),
  `order_status` enum('Pending','Received','Cancelled') NOT NULL DEFAULT 'Pending',
  PRIMARY KEY (`order_id`),
  KEY `fk_purchase_order_supplier_idx` (`supplier_id`),
  CONSTRAINT `fk_purchase_order_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`supplier_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product_supplier`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_supplier` (
  `product_supplier_id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `supplier_id` int NOT NULL,
  `supplier_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `supplier_unit` int NOT NULL DEFAULT '1',
  `effective_date` date NOT NULL DEFAULT (curdate()),
  PRIMARY KEY (`product_supplier_id`),
  KEY `fk_product_supplier_product_idx` (`product_id`),
  KEY `fk_product_supplier_supplier1_idx` (`supplier_id`),
  CONSTRAINT `fk_product_supplier_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`),
  CONSTRAINT `fk_product_supplier_supplier1` FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`supplier_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_consumables`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_consumables` (
  `job_consumables_id` int NOT NULL AUTO_INCREMENT,
  `qty_of_product_used` int NOT NULL DEFAULT '0',
  `product_id` int NOT NULL,
  `job_id` int NOT NULL,
  PRIMARY KEY (`job_consumables_id`),
  KEY `fk_job_consumables_product1_idx` (`product_id`),
  KEY `fk_job_consumables_job1_idx` (`job_id`),
  CONSTRAINT `fk_job_consumables_job1` FOREIGN KEY (`job_id`) REFERENCES `job` (`job_id`),
  CONSTRAINT `fk_job_consumables_product1` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_instance`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_instance` (
  `job_instance_id` int NOT NULL AUTO_INCREMENT,
  `job_id` int NOT NULL,
  `operation_date` datetime NOT NULL,
  `status` enum('Scheduled','Completed','Cancelled') NOT NULL DEFAULT 'Scheduled',
  PRIMARY KEY (`job_instance_id`),
  KEY `fk_job_instance_job_idx` (`job_id`),
  CONSTRAINT `fk_job_instance_job` FOREIGN KEY (`job_id`) REFERENCES `job` (`job_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sale`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sale` (
  `sale_id` int NOT NULL AUTO_INCREMENT,
  `sold_qty` int NOT NULL,
  `sold_date` datetime NOT NULL DEFAULT (curdate()),
  `product_id` int NOT NULL,
  PRIMARY KEY (`sale_id`),
  KEY `fk_sale_product1_idx` (`product_id`),
  CONSTRAINT `fk_sale_product1` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inventory_update`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory_update` (
  `update_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL,
  `update_date` datetime NOT NULL DEFAULT (curdate()),
  `update_note` text,
  PRIMARY KEY (`update_id`),
  KEY `fk_inventory_update_po_idx` (`order_id`),
  CONSTRAINT `fk_inventory_update_po` FOREIGN KEY (`order_id`) REFERENCES `purchase_order` (`order_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `purchase_order_item`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_order_item` (
  `po_item_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `product_id` int NOT NULL,
  `order_amount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`po_item_id`),
  KEY `fk_po_item_order_idx` (`order_id`),
  KEY `fk_po_item_product_idx` (`product_id`),
  CONSTRAINT `fk_po_item_order` FOREIGN KEY (`order_id`) REFERENCES `purchase_order` (`order_id`),
  CONSTRAINT `fk_po_item_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inventory_update_item`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory_update_item` (
  `update_item_id` int NOT NULL AUTO_INCREMENT,
  `update_id` int NOT NULL,
  `product_id` int NOT NULL,
  `update_amount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`update_item_id`),
  KEY `fk_update_item_update_idx` (`update_id`),
  KEY `fk_update_item_product_idx` (`product_id`),
  CONSTRAINT `fk_update_item_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`),
  CONSTRAINT `fk_update_item_update` FOREIGN KEY (`update_id`) REFERENCES `inventory_update` (`update_id`)
  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;