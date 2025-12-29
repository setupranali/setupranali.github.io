-- =============================================================================
-- MySQL Sample Data for SetuPranali Demo
-- =============================================================================

CREATE TABLE IF NOT EXISTS sales (
    sale_id VARCHAR(50) PRIMARY KEY,
    sale_date DATE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    region VARCHAR(50),
    salesperson VARCHAR(100),
    amount DECIMAL(12,2) NOT NULL,
    units_sold INT NOT NULL,
    tenant_id VARCHAR(50) DEFAULT 'demo'
);

INSERT INTO sales VALUES
('S001', '2024-01-05', 'Laptop Pro', 'Electronics', 'North', 'John', 1299.99, 1, 'demo'),
('S002', '2024-01-07', 'Wireless Mouse', 'Electronics', 'South', 'Jane', 29.99, 5, 'demo'),
('S003', '2024-01-10', 'Office Chair', 'Furniture', 'East', 'Bob', 299.00, 2, 'demo'),
('S004', '2024-01-12', 'Desk Lamp', 'Home', 'West', 'Alice', 49.99, 3, 'demo'),
('S005', '2024-01-15', 'Monitor 27"', 'Electronics', 'North', 'John', 349.99, 2, 'demo'),
('S006', '2024-01-18', 'Keyboard', 'Electronics', 'South', 'Jane', 79.99, 4, 'demo'),
('S007', '2024-01-20', 'Standing Desk', 'Furniture', 'East', 'Bob', 599.00, 1, 'demo'),
('S008', '2024-01-22', 'Webcam HD', 'Electronics', 'West', 'Alice', 89.99, 2, 'demo'),
('S009', '2024-01-25', 'Headphones', 'Electronics', 'North', 'John', 199.99, 3, 'demo'),
('S010', '2024-01-28', 'USB Hub', 'Electronics', 'South', 'Jane', 39.99, 6, 'demo'),
('S011', '2024-02-02', 'Laptop Pro', 'Electronics', 'East', 'Bob', 1299.99, 2, 'demo'),
('S012', '2024-02-05', 'Office Chair', 'Furniture', 'West', 'Alice', 299.00, 1, 'demo'),
('S013', '2024-02-08', 'Monitor 32"', 'Electronics', 'North', 'John', 449.99, 1, 'demo'),
('S014', '2024-02-10', 'Desk Organizer', 'Home', 'South', 'Jane', 29.99, 4, 'demo'),
('S015', '2024-02-12', 'Laptop Stand', 'Accessories', 'East', 'Bob', 69.99, 3, 'demo');

CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_category ON sales(category);
CREATE INDEX idx_sales_region ON sales(region);

