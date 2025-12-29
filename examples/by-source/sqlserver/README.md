# SQL Server Examples

Connect SetuPranali to Microsoft SQL Server.

## Overview

- SQL Server, Azure SQL, Azure Synapse support
- Windows and SQL authentication
- Active Directory integration

## Connection Configuration

### SQL Authentication

```yaml
sources:
  sqlserver:
    type: sqlserver
    connection:
      host: localhost
      port: 1433
      database: Analytics
      user: ${MSSQL_USER}
      password: ${MSSQL_PASSWORD}
```

### Windows Authentication

```yaml
sources:
  sqlserver:
    type: sqlserver
    connection:
      host: sqlserver.domain.local
      port: 1433
      database: Analytics
      trusted_connection: true
```

### Azure SQL Database

```yaml
sources:
  azure_sql:
    type: sqlserver
    connection:
      host: your-server.database.windows.net
      port: 1433
      database: Analytics
      user: ${AZURE_SQL_USER}
      password: ${AZURE_SQL_PASSWORD}
      encrypt: true
      trust_server_certificate: false
```

### Azure Synapse Analytics

```yaml
sources:
  synapse:
    type: sqlserver
    connection:
      host: your-workspace.sql.azuresynapse.net
      port: 1433
      database: your_pool
      user: ${SYNAPSE_USER}
      password: ${SYNAPSE_PASSWORD}
      encrypt: true
```

## SQL Server-Specific Features

### Date Functions

```yaml
dimensions:
  - name: order_month
    type: string
    sql: FORMAT(order_date, 'yyyy-MM')
    
  - name: order_year
    type: number
    sql: YEAR(order_date)
    
  - name: quarter
    type: string
    sql: CONCAT('Q', DATEPART(QUARTER, order_date))
```

### String Functions

```yaml
dimensions:
  - name: customer_initials
    type: string
    sql: LEFT(customer_name, 1) + LEFT(SUBSTRING(customer_name, CHARINDEX(' ', customer_name) + 1, 100), 1)
```

### Window Functions

```yaml
metrics:
  - name: running_total
    type: custom
    sql: SUM(amount) OVER (ORDER BY order_date ROWS UNBOUNDED PRECEDING)
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: sqlserver
    table: dbo.Orders
    
    dimensions:
      - name: OrderID
        type: number
        sql: OrderID
        primary_key: true
        
      - name: OrderDate
        type: date
        sql: OrderDate
        
      - name: CustomerID
        type: string
        sql: CustomerID
        
      - name: Region
        type: string
        sql: Region
    
    metrics:
      - name: Revenue
        type: sum
        sql: TotalAmount
        
      - name: OrderCount
        type: count
        sql: OrderID
```

## Docker Setup

```yaml
version: '3.8'
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - MSSQL_SA_PASSWORD=YourStrong@Password123
    ports:
      - "1433:1433"

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - MSSQL_HOST=sqlserver
      - MSSQL_USER=sa
      - MSSQL_PASSWORD=YourStrong@Password123
```

## Troubleshooting

### Connection Timeout
- Check firewall allows port 1433
- For Azure SQL, add client IP to firewall rules

### Login Failed
- Verify SQL authentication is enabled
- Check user has database access

### TLS/SSL Issues
- Set `encrypt: true` and `trust_server_certificate: true` for testing

