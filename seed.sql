USE inventory_db;

-- Clear existing data if re-running seed script
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Sale;
TRUNCATE TABLE Job_Product;
TRUNCATE TABLE Job;
TRUNCATE TABLE Inventory_Order;
TRUNCATE TABLE Product_Supplier;
TRUNCATE TABLE Supplier;
TRUNCATE TABLE Product;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Insert 5 Cosmetic Practice Products (Retail & Professional Backbar)
INSERT INTO Product (product_id, product_name, product_price) VALUES
(1, 'Hyaluronic Acid Hydrating Serum (30ml)', 650.00),
(2, 'Vitamin C Brightening Serum (30ml)', 720.00),
(3, 'Clinical Repair Peptide Cream (50ml)', 850.00),
(4, 'Broad Spectrum SPF 50 Mineral Sunscreen', 450.00),
(5, 'Gentle Purifying Cleanser (200ml)', 380.00);

-- 2. Insert 3 Cosmetic/Medical Suppliers
INSERT INTO Supplier (supplier_id, supplier_name, supplier_from_date, reason_for_changing_supplier) VALUES
(1, 'DermaMed Laboratory Supplies', '2024-01-15', 'Primary vendor for medical-grade active ingredients and serums.'),
(2, 'Apex Clinical Formulations', '2024-06-01', 'Switched cream manufacturer for improved organic preservation standards.'),
(3, 'Pure Botanicals & Extracts', '2025-03-10', 'Added backup supplier for specialized botanical extracts and sunscreens.');

-- 3. Link Products to Suppliers (Product_Supplier)
INSERT INTO Product_Supplier (product_id, supplier_id) VALUES
(1, 1), (1, 3),
(2, 1),
(3, 2),
(4, 1), (4, 3),
(5, 2);

-- 4. Insert 2 Clinical Jobs / Treatments
INSERT INTO Job (job_id, job_name) VALUES
(1, 'Signature Hydrating Facial & Peel Protocol'),
(2, 'Advanced Microneedling & Infusion Treatment');

-- 5. Link Products to Jobs (Job_Product - Quantities used per treatment cycle/batch)
INSERT INTO Job_Product (job_id, product_id, qty_of_products_used_in_job) VALUES
(1, 1, 15), -- Serums used in facial protocol
(1, 5, 20), -- Cleanser used in facial prep
(2, 1, 30), -- Serums used post-microneedling
(2, 2, 25), -- Vitamin C used in post-care
(2, 3, 20); -- Peptide cream used for barrier repair

-- 6. Inventory Orders for an Entire Year (2026) with Seasonal Fluctuations
-- High demand / restock months: Pre-summer/holiday prep (Nov/Dec) and autumn peel season (March/April)
INSERT INTO Inventory_Order (product_id, inventory_order_date, inventory_update_date) VALUES
-- January (Post-holiday slow down)
(1, '2026-01-10', '2026-01-12'),
(4, '2026-01-10', '2026-01-12'),
-- February (Steady baseline)
(2, '2026-02-14', '2026-02-16'),
(5, '2026-02-14', '2026-02-16'),
-- March (Autumn Peel Season Spike)
(1, '2026-03-05', '2026-03-07'),
(2, '2026-03-05', '2026-03-07'),
(3, '2026-03-05', '2026-03-07'),
(4, '2026-03-05', '2026-03-07'),
(5, '2026-03-05', '2026-03-07'),
-- April (Autumn Peel Season Spike)
(1, '2026-04-10', '2026-04-12'),
(3, '2026-04-10', '2026-04-12'),
(5, '2026-04-10', '2026-04-12'),
-- May (Moderate)
(2, '2026-05-12', '2026-05-14'),
(4, '2026-05-12', '2026-05-14'),
-- June (Mid-year check)
(1, '2026-06-15', '2026-06-17'),
(3, '2026-06-15', '2026-06-17'),
-- July (Winter lull)
(2, '2026-07-20', '2026-07-22'),
-- August (Winter lull)
(4, '2026-08-18', '2026-08-20'),
-- September (Spring prep)
(1, '2026-09-10', '2026-09-12'),
(3, '2026-09-10', '2026-09-12'),
(5, '2026-09-10', '2026-09-12'),
-- October (Pre-summer stock build)
(1, '2026-10-05', '2026-10-07'),
(2, '2026-10-05', '2026-10-07'),
(3, '2026-10-05', '2026-10-07'),
(4, '2026-10-05', '2026-10-07'),
(5, '2026-10-05', '2026-10-07'),
-- November (Peak Summer & Holiday Retail Rush)
(1, '2026-11-08', '2026-11-10'),
(2, '2026-11-08', '2026-11-10'),
(3, '2026-11-08', '2026-11-10'),
(4, '2026-11-08', '2026-11-10'),
(5, '2026-11-08', '2026-11-10'),
-- December (Holiday Wind-down)
(1, '2026-12-05', '2026-12-07'),
(4, '2026-12-05', '2026-12-07');

-- 7. Sales Records for 2026 (Matching Aesthetic Practice Seasonal Demand Patterns)
INSERT INTO Sale (product_id, sold_quantity, products_sold_date) VALUES
-- January (Slow retail month)
(1, 12, '2026-01-15'), (4, 18, '2026-01-15'),
-- February (Steady)
(1, 15, '2026-02-18'), (5, 14, '2026-02-18'),
-- March (Autumn Peel Season Spike)
(1, 45, '2026-03-12'), (2, 38, '2026-03-12'), (3, 30, '2026-03-12'), (4, 25, '2026-03-12'), (5, 40, '2026-03-12'),
-- April (High Treatment Demand)
(1, 50, '2026-04-16'), (2, 42, '2026-04-16'), (3, 35, '2026-04-16'), (5, 45, '2026-04-16'),
-- May (Moderate)
(1, 20, '2026-05-20'), (4, 22, '2026-05-20'),
-- June (Moderate)
(1, 22, '2026-06-22'), (3, 18, '2026-06-22'), (5, 20, '2026-06-22'),
-- July (Winter Lull)
(1, 14, '2026-07-15'), (4, 15, '2026-07-15'),
-- August (Winter Lull)
(1, 16, '2026-08-14'), (4, 16, '2026-08-14'),
-- September (Spring Skin Prep)
(1, 35, '2026-09-18'), (2, 30, '2026-09-18'), (4, 40, '2026-09-18'), (5, 30, '2026-09-18'),
-- October (Pre-Summer Campaign)
(1, 55, '2026-10-12'), (2, 45, '2026-10-12'), (3, 40, '2026-10-12'), (4, 65, '2026-10-12'), (5, 50, '2026-10-12'),
-- November (Peak Summer Sunscreen & Holiday Gift Rush)
(1, 75, '2026-11-15'), (2, 60, '2026-11-15'), (3, 55, '2026-11-15'), (4, 95, '2026-11-15'), (5, 70, '2026-11-15'),
-- December (Holiday Sales Wind-down)
(1, 30, '2026-12-10'), (4, 40, '2026-12-10'), (2, 25, '2026-12-10');