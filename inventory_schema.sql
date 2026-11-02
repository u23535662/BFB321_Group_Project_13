CREATE SCHEMA IF NOT EXISTS inventory_db;
USE inventory_db;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Sale;
DROP TABLE IF EXISTS Job_Product;
DROP TABLE IF EXISTS Inventory_Order;
DROP TABLE IF EXISTS Product_Supplier;
DROP TABLE IF EXISTS Job;
DROP TABLE IF EXISTS Supplier;
DROP TABLE IF EXISTS Product;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Product Table
CREATE TABLE Product (
    product_id      INT AUTO_INCREMENT  PRIMARY KEY,
    product_name    VARCHAR(255)        NOT NULL,
    product_price   DECIMAL(10, 2)      NOT NULL
);

-- 2. Supplier Table
CREATE TABLE Supplier (
    supplier_id                     INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name                   VARCHAR(255)       NOT NULL,
    supplier_from_date              DATE               NOT NULL    DEFAULT (CURRENT_DATE),
    reason_for_changing_supplier    TEXT
);

-- 3. Product-Supplier Junction Table (Many-to-Many)
CREATE TABLE Product_Supplier (
    product_id  INT NOT NULL,
    supplier_id INT NOT NULL,
    PRIMARY KEY (product_id, supplier_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id) ON DELETE CASCADE
);

-- 4. Inventory Order Table
CREATE TABLE Inventory_Order (
    inventory_id          INT AUTO_INCREMENT PRIMARY KEY,
    product_id            INT  NOT NULL,
    inventory_order_date  DATE NOT NULL DEFAULT (CURRENT_DATE),
    inventory_update_date DATE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);

-- 5. Job Table
CREATE TABLE Job (
    job_id   INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL
);

-- 6. Job-Product Junction Table (Products used in job)
CREATE TABLE Job_Product (
    job_id                      INT NOT NULL,
    product_id                  INT NOT NULL,
    qty_of_products_used_in_job INT NOT NULL,
    PRIMARY KEY (job_id, product_id),
    FOREIGN KEY (job_id) REFERENCES Job(job_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);

-- 7. Sale Table (Products sold date & sold quantity)
CREATE TABLE Sale (
    sale_id            INT AUTO_INCREMENT PRIMARY KEY,
    product_id         INT,
    sold_quantity      INT NOT NULL DEFAULT 1,
    products_sold_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);