CREATE DATABASE IF NOT EXISTS `stock_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `stock_db`;

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `supplier`
--

DROP TABLE IF EXISTS `supplier`;
CREATE TABLE `supplier` (
  `supplier_id` int NOT NULL AUTO_INCREMENT,
  `supplier_name` varchar(255) NOT NULL,
  `supplier_from_date` date NOT NULL DEFAULT (curdate()),
  `reason_for_changing_supplier` text,
  `replaces_supplier_id` int DEFAULT NULL,
  `contact_email` varchar(160) NOT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`supplier_id`),
  KEY `fk_supplier_supplier1_idx` (`replaces_supplier_id`),
  CONSTRAINT `fk_supplier_supplier1` FOREIGN KEY (`replaces_supplier_id`) REFERENCES `supplier` (`supplier_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
CREATE TABLE `product` (
  `product_id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `product_name` varchar(255) NOT NULL,
  `product_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `supplier_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `units_per_package` int NOT NULL DEFAULT '1',
  `product_holding_cost` decimal(10,2) NOT NULL DEFAULT '0.00',
  `year_starting_inventory` int NOT NULL DEFAULT '0',
  `storage_location` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`product_id`),
  KEY `fk_product_supplier_idx` (`supplier_id`),
  CONSTRAINT `fk_product_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`supplier_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_product_holding_nonneg` CHECK ((`product_holding_cost` >= 0)),
  CONSTRAINT `chk_product_price_nonneg` CHECK ((`product_price` >= 0)),
  CONSTRAINT `chk_product_supplier_price_nonneg` CHECK ((`supplier_price` >= 0)),
  CONSTRAINT `chk_product_units_pos` CHECK ((`units_per_package` > 0)),
  CONSTRAINT `chk_product_start_inv_nonneg` CHECK ((`year_starting_inventory` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `purchase_order`
--

DROP TABLE IF EXISTS `purchase_order`;
CREATE TABLE `purchase_order` (
  `order_id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `order_date` date NOT NULL DEFAULT (curdate()),
  `order_status` enum('Pending','Received','Cancelled') NOT NULL DEFAULT 'Pending',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`order_id`),
  KEY `fk_purchase_order_supplier_idx` (`supplier_id`),
  CONSTRAINT `fk_purchase_order_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `supplier` (`supplier_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=86 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `purchase_order_item`
--

DROP TABLE IF EXISTS `purchase_order_item`;
CREATE TABLE `purchase_order_item` (
  `po_item_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `product_id` int NOT NULL,
  `order_amount` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`po_item_id`),
  UNIQUE KEY `uq_po_item_order_product` (`order_id`,`product_id`),
  KEY `fk_po_item_order_idx` (`order_id`),
  KEY `fk_po_item_product_idx` (`product_id`),
  CONSTRAINT `fk_po_item_order` FOREIGN KEY (`order_id`) REFERENCES `purchase_order` (`order_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_po_item_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_po_item_qty_pos` CHECK ((`order_amount` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=255 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `inventory_update`
-- (order_id is now mandatory so every update belongs to a specific PO)
--

DROP TABLE IF EXISTS `inventory_update`;
CREATE TABLE `inventory_update` (
  `update_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `update_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_note` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`update_id`),
  KEY `fk_inventory_update_po_idx` (`order_id`),
  CONSTRAINT `fk_inventory_update_po` FOREIGN KEY (`order_id`) REFERENCES `purchase_order` (`order_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=84 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `inventory_update_item`
--

DROP TABLE IF EXISTS `inventory_update_item`;
CREATE TABLE `inventory_update_item` (
  `update_item_id` int NOT NULL AUTO_INCREMENT,
  `update_id` int NOT NULL,
  `product_id` int NOT NULL,
  `update_amount` int NOT NULL DEFAULT '0',
  `expiry_date` date NOT NULL DEFAULT (curdate()),
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`update_item_id`),
  KEY `fk_update_item_update_idx` (`update_id`),
  KEY `fk_update_item_product_idx` (`product_id`),
  CONSTRAINT `fk_update_item_product` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_update_item_update` FOREIGN KEY (`update_id`) REFERENCES `inventory_update` (`update_id`) ON DELETE CASCADE,
  CONSTRAINT `chk_update_item_qty_nonzero` CHECK ((`update_amount` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=248 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `sale`
--

DROP TABLE IF EXISTS `sale`;
CREATE TABLE `sale` (
  `sale_id` int NOT NULL AUTO_INCREMENT,
  `sold_qty` int NOT NULL,
  `sold_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `product_id` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sale_id`),
  KEY `fk_sale_product1_idx` (`product_id`),
  CONSTRAINT `fk_sale_product1` FOREIGN KEY (`product_id`) REFERENCES `product` (`product_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_sale_qty_pos` CHECK ((`sold_qty` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=3601 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
