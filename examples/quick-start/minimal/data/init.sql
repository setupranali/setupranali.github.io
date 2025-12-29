-- =============================================================================
-- Sample Orders Database for SetuPranali Demo
-- =============================================================================
-- Run this to create the demo database:
-- sqlite3 orders.db < init.sql
-- =============================================================================

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_date DATE NOT NULL,
    customer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    region TEXT NOT NULL,
    category TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    tenant_id TEXT DEFAULT 'demo'
);

-- Insert sample data
INSERT INTO orders (order_id, order_date, customer_id, status, region, category, amount, quantity, tenant_id) VALUES
-- January 2024
('ORD-001', '2024-01-05', 'CUST-101', 'delivered', 'North', 'Electronics', 299.99, 1, 'demo'),
('ORD-002', '2024-01-07', 'CUST-102', 'delivered', 'South', 'Clothing', 89.50, 2, 'demo'),
('ORD-003', '2024-01-10', 'CUST-103', 'delivered', 'East', 'Home', 156.00, 1, 'demo'),
('ORD-004', '2024-01-12', 'CUST-101', 'delivered', 'North', 'Electronics', 549.99, 1, 'demo'),
('ORD-005', '2024-01-15', 'CUST-104', 'shipped', 'West', 'Sports', 75.00, 3, 'demo'),
('ORD-006', '2024-01-18', 'CUST-105', 'delivered', 'North', 'Clothing', 120.00, 2, 'demo'),
('ORD-007', '2024-01-20', 'CUST-102', 'delivered', 'South', 'Electronics', 899.99, 1, 'demo'),
('ORD-008', '2024-01-22', 'CUST-106', 'cancelled', 'East', 'Home', 245.00, 1, 'demo'),
('ORD-009', '2024-01-25', 'CUST-103', 'delivered', 'East', 'Sports', 199.99, 2, 'demo'),
('ORD-010', '2024-01-28', 'CUST-107', 'delivered', 'West', 'Clothing', 65.00, 1, 'demo'),

-- February 2024
('ORD-011', '2024-02-02', 'CUST-108', 'delivered', 'North', 'Electronics', 1299.99, 1, 'demo'),
('ORD-012', '2024-02-05', 'CUST-101', 'delivered', 'North', 'Home', 89.00, 2, 'demo'),
('ORD-013', '2024-02-08', 'CUST-109', 'shipped', 'South', 'Sports', 250.00, 1, 'demo'),
('ORD-014', '2024-02-10', 'CUST-110', 'delivered', 'West', 'Clothing', 175.50, 3, 'demo'),
('ORD-015', '2024-02-12', 'CUST-102', 'delivered', 'South', 'Electronics', 449.99, 1, 'demo'),
('ORD-016', '2024-02-15', 'CUST-111', 'pending', 'East', 'Home', 320.00, 1, 'demo'),
('ORD-017', '2024-02-18', 'CUST-103', 'delivered', 'East', 'Clothing', 95.00, 2, 'demo'),
('ORD-018', '2024-02-20', 'CUST-112', 'delivered', 'North', 'Sports', 180.00, 1, 'demo'),
('ORD-019', '2024-02-22', 'CUST-104', 'shipped', 'West', 'Electronics', 699.99, 1, 'demo'),
('ORD-020', '2024-02-25', 'CUST-113', 'delivered', 'South', 'Home', 420.00, 2, 'demo'),

-- March 2024
('ORD-021', '2024-03-01', 'CUST-101', 'delivered', 'North', 'Clothing', 210.00, 3, 'demo'),
('ORD-022', '2024-03-04', 'CUST-114', 'delivered', 'East', 'Electronics', 799.99, 1, 'demo'),
('ORD-023', '2024-03-07', 'CUST-105', 'delivered', 'North', 'Sports', 145.00, 2, 'demo'),
('ORD-024', '2024-03-10', 'CUST-115', 'cancelled', 'West', 'Home', 560.00, 1, 'demo'),
('ORD-025', '2024-03-12', 'CUST-102', 'delivered', 'South', 'Clothing', 88.00, 1, 'demo'),
('ORD-026', '2024-03-15', 'CUST-116', 'delivered', 'East', 'Electronics', 1599.99, 1, 'demo'),
('ORD-027', '2024-03-18', 'CUST-103', 'shipped', 'East', 'Home', 275.00, 2, 'demo'),
('ORD-028', '2024-03-20', 'CUST-117', 'delivered', 'North', 'Sports', 320.00, 1, 'demo'),
('ORD-029', '2024-03-22', 'CUST-106', 'delivered', 'East', 'Clothing', 150.00, 2, 'demo'),
('ORD-030', '2024-03-25', 'CUST-118', 'pending', 'West', 'Electronics', 2499.99, 1, 'demo'),

-- Multi-tenant data (for RLS demo)
('ORD-T1-001', '2024-03-01', 'CUST-T1-01', 'delivered', 'North', 'Electronics', 599.99, 1, 'tenant_a'),
('ORD-T1-002', '2024-03-05', 'CUST-T1-02', 'delivered', 'South', 'Clothing', 125.00, 2, 'tenant_a'),
('ORD-T1-003', '2024-03-10', 'CUST-T1-01', 'shipped', 'East', 'Home', 350.00, 1, 'tenant_a'),
('ORD-T2-001', '2024-03-02', 'CUST-T2-01', 'delivered', 'West', 'Sports', 275.00, 1, 'tenant_b'),
('ORD-T2-002', '2024-03-08', 'CUST-T2-02', 'delivered', 'North', 'Electronics', 899.99, 1, 'tenant_b'),
('ORD-T2-003', '2024-03-15', 'CUST-T2-01', 'pending', 'South', 'Clothing', 180.00, 3, 'tenant_b');

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_region ON orders(region);
CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders(tenant_id);

-- Verify data
SELECT 'Total Orders: ' || COUNT(*) FROM orders;
SELECT 'Total Revenue: $' || printf('%.2f', SUM(amount)) FROM orders;

