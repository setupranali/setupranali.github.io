-- =============================================================================
-- Sample Data for SetuPranali PostgreSQL Demo
-- =============================================================================

-- Insert Customers
INSERT INTO customers (customer_id, name, email, segment, country, city, lifetime_value, tenant_id) VALUES
('CUST-001', 'Alice Johnson', 'alice@example.com', 'Premium', 'USA', 'New York', 5420.00, 'demo'),
('CUST-002', 'Bob Smith', 'bob@example.com', 'Standard', 'USA', 'Los Angeles', 2150.00, 'demo'),
('CUST-003', 'Carol White', 'carol@example.com', 'Premium', 'Canada', 'Toronto', 8900.00, 'demo'),
('CUST-004', 'David Brown', 'david@example.com', 'Basic', 'UK', 'London', 890.00, 'demo'),
('CUST-005', 'Eve Davis', 'eve@example.com', 'Standard', 'Germany', 'Berlin', 3200.00, 'demo'),
('CUST-006', 'Frank Miller', 'frank@example.com', 'Premium', 'USA', 'Chicago', 12500.00, 'demo'),
('CUST-007', 'Grace Lee', 'grace@example.com', 'Standard', 'Japan', 'Tokyo', 4100.00, 'demo'),
('CUST-008', 'Henry Wilson', 'henry@example.com', 'Basic', 'Australia', 'Sydney', 650.00, 'demo'),
('CUST-009', 'Ivy Chen', 'ivy@example.com', 'Premium', 'Singapore', 'Singapore', 9800.00, 'demo'),
('CUST-010', 'Jack Taylor', 'jack@example.com', 'Standard', 'USA', 'Seattle', 2800.00, 'demo'),
-- Tenant A customers
('CUST-A-001', 'Tenant A User 1', 'a1@tenant-a.com', 'Premium', 'USA', 'Boston', 5000.00, 'tenant_a'),
('CUST-A-002', 'Tenant A User 2', 'a2@tenant-a.com', 'Standard', 'USA', 'Miami', 2500.00, 'tenant_a'),
-- Tenant B customers
('CUST-B-001', 'Tenant B User 1', 'b1@tenant-b.com', 'Standard', 'UK', 'Manchester', 3000.00, 'tenant_b'),
('CUST-B-002', 'Tenant B User 2', 'b2@tenant-b.com', 'Premium', 'UK', 'Edinburgh', 7500.00, 'tenant_b');

-- Insert Products
INSERT INTO products (product_id, name, category, brand, supplier, price, cost, stock_quantity) VALUES
('PROD-001', 'Wireless Mouse', 'Electronics', 'TechBrand', 'Supplier A', 29.99, 15.00, 500),
('PROD-002', 'Mechanical Keyboard', 'Electronics', 'TechBrand', 'Supplier A', 89.99, 45.00, 300),
('PROD-003', 'HD Monitor 27"', 'Electronics', 'ViewMax', 'Supplier B', 299.99, 180.00, 150),
('PROD-004', 'USB-C Hub', 'Electronics', 'TechBrand', 'Supplier A', 49.99, 25.00, 400),
('PROD-005', 'Cotton T-Shirt', 'Clothing', 'FashionCo', 'Supplier C', 24.99, 8.00, 1000),
('PROD-006', 'Denim Jeans', 'Clothing', 'FashionCo', 'Supplier C', 59.99, 20.00, 600),
('PROD-007', 'Running Shoes', 'Sports', 'SportGear', 'Supplier D', 89.99, 40.00, 400),
('PROD-008', 'Yoga Mat', 'Sports', 'SportGear', 'Supplier D', 34.99, 12.00, 800),
('PROD-009', 'Coffee Table', 'Home', 'HomeStyle', 'Supplier E', 149.99, 70.00, 100),
('PROD-010', 'Desk Lamp', 'Home', 'HomeStyle', 'Supplier E', 39.99, 18.00, 350);

-- Insert Orders (Demo tenant)
INSERT INTO orders (order_id, order_date, customer_id, status, region, category, payment_method, amount, quantity, tenant_id) VALUES
-- January 2024
('ORD-001', '2024-01-03', 'CUST-001', 'delivered', 'North', 'Electronics', 'Credit Card', 299.99, 1, 'demo'),
('ORD-002', '2024-01-05', 'CUST-002', 'delivered', 'West', 'Clothing', 'PayPal', 84.98, 2, 'demo'),
('ORD-003', '2024-01-08', 'CUST-003', 'delivered', 'North', 'Electronics', 'Credit Card', 89.99, 1, 'demo'),
('ORD-004', '2024-01-10', 'CUST-004', 'delivered', 'East', 'Sports', 'Debit Card', 124.98, 2, 'demo'),
('ORD-005', '2024-01-12', 'CUST-001', 'delivered', 'North', 'Home', 'Credit Card', 189.98, 2, 'demo'),
('ORD-006', '2024-01-15', 'CUST-005', 'delivered', 'East', 'Electronics', 'PayPal', 49.99, 1, 'demo'),
('ORD-007', '2024-01-18', 'CUST-006', 'delivered', 'South', 'Clothing', 'Credit Card', 59.99, 1, 'demo'),
('ORD-008', '2024-01-20', 'CUST-007', 'shipped', 'West', 'Electronics', 'Credit Card', 419.98, 2, 'demo'),
('ORD-009', '2024-01-22', 'CUST-008', 'delivered', 'South', 'Sports', 'Debit Card', 34.99, 1, 'demo'),
('ORD-010', '2024-01-25', 'CUST-009', 'delivered', 'East', 'Home', 'PayPal', 149.99, 1, 'demo'),

-- February 2024
('ORD-011', '2024-02-02', 'CUST-010', 'delivered', 'West', 'Electronics', 'Credit Card', 29.99, 1, 'demo'),
('ORD-012', '2024-02-05', 'CUST-001', 'delivered', 'North', 'Clothing', 'Credit Card', 109.98, 2, 'demo'),
('ORD-013', '2024-02-08', 'CUST-003', 'delivered', 'North', 'Electronics', 'PayPal', 299.99, 1, 'demo'),
('ORD-014', '2024-02-10', 'CUST-002', 'cancelled', 'West', 'Sports', 'Credit Card', 89.99, 1, 'demo'),
('ORD-015', '2024-02-12', 'CUST-006', 'delivered', 'South', 'Home', 'Debit Card', 189.98, 2, 'demo'),
('ORD-016', '2024-02-15', 'CUST-004', 'delivered', 'East', 'Electronics', 'PayPal', 139.98, 2, 'demo'),
('ORD-017', '2024-02-18', 'CUST-009', 'shipped', 'East', 'Clothing', 'Credit Card', 84.98, 2, 'demo'),
('ORD-018', '2024-02-20', 'CUST-007', 'delivered', 'West', 'Sports', 'Credit Card', 124.98, 2, 'demo'),
('ORD-019', '2024-02-22', 'CUST-005', 'delivered', 'East', 'Home', 'Debit Card', 39.99, 1, 'demo'),
('ORD-020', '2024-02-25', 'CUST-008', 'pending', 'South', 'Electronics', 'PayPal', 89.99, 1, 'demo'),

-- March 2024
('ORD-021', '2024-03-01', 'CUST-001', 'delivered', 'North', 'Electronics', 'Credit Card', 599.98, 2, 'demo'),
('ORD-022', '2024-03-04', 'CUST-010', 'delivered', 'West', 'Clothing', 'PayPal', 59.99, 1, 'demo'),
('ORD-023', '2024-03-07', 'CUST-003', 'delivered', 'North', 'Sports', 'Credit Card', 179.98, 2, 'demo'),
('ORD-024', '2024-03-10', 'CUST-006', 'shipped', 'South', 'Home', 'Debit Card', 149.99, 1, 'demo'),
('ORD-025', '2024-03-12', 'CUST-002', 'delivered', 'West', 'Electronics', 'Credit Card', 79.98, 2, 'demo'),
('ORD-026', '2024-03-15', 'CUST-009', 'delivered', 'East', 'Clothing', 'PayPal', 134.98, 2, 'demo'),
('ORD-027', '2024-03-18', 'CUST-004', 'delivered', 'East', 'Sports', 'Credit Card', 34.99, 1, 'demo'),
('ORD-028', '2024-03-20', 'CUST-007', 'pending', 'West', 'Electronics', 'Debit Card', 299.99, 1, 'demo'),
('ORD-029', '2024-03-22', 'CUST-005', 'delivered', 'East', 'Home', 'PayPal', 189.98, 2, 'demo'),
('ORD-030', '2024-03-25', 'CUST-008', 'delivered', 'South', 'Clothing', 'Credit Card', 24.99, 1, 'demo'),

-- Tenant A orders
('ORD-A-001', '2024-03-01', 'CUST-A-001', 'delivered', 'North', 'Electronics', 'Credit Card', 599.99, 1, 'tenant_a'),
('ORD-A-002', '2024-03-05', 'CUST-A-002', 'delivered', 'South', 'Clothing', 'PayPal', 84.98, 2, 'tenant_a'),
('ORD-A-003', '2024-03-10', 'CUST-A-001', 'shipped', 'North', 'Sports', 'Credit Card', 124.98, 2, 'tenant_a'),

-- Tenant B orders
('ORD-B-001', '2024-03-02', 'CUST-B-001', 'delivered', 'East', 'Home', 'Debit Card', 189.98, 2, 'tenant_b'),
('ORD-B-002', '2024-03-08', 'CUST-B-002', 'delivered', 'West', 'Electronics', 'Credit Card', 419.98, 2, 'tenant_b'),
('ORD-B-003', '2024-03-15', 'CUST-B-001', 'pending', 'East', 'Clothing', 'PayPal', 59.99, 1, 'tenant_b');

-- Update customer lifetime values based on orders
UPDATE customers c SET lifetime_value = (
    SELECT COALESCE(SUM(o.amount), 0) 
    FROM orders o 
    WHERE o.customer_id = c.customer_id AND o.status != 'cancelled'
);

