# Oracle Database Examples

Connect SetuPranali to Oracle Database.

## Overview

- Oracle Database, Oracle Cloud, Autonomous DB support
- Easy Connect and TNS connection methods
- Wallet-based authentication for cloud

## Connection Configuration

### Easy Connect

```yaml
sources:
  oracle_db:
    type: oracle
    connection:
      host: localhost
      port: 1521
      service_name: ORCL
      user: ${ORACLE_USER}
      password: ${ORACLE_PASSWORD}
```

### TNS Connection

```yaml
sources:
  oracle_db:
    type: oracle
    connection:
      tns_name: PROD_DB
      user: ${ORACLE_USER}
      password: ${ORACLE_PASSWORD}
      tns_admin: /app/oracle/network/admin
```

### Oracle Autonomous Database (Cloud)

```yaml
sources:
  oracle_adb:
    type: oracle
    connection:
      dsn: "(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.region.oraclecloud.com))(connect_data=(service_name=xxx_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))"
      user: ADMIN
      password: ${ORACLE_PASSWORD}
      wallet_location: /app/wallet
      wallet_password: ${WALLET_PASSWORD}
```

## Oracle-Specific Features

### Date Functions

```yaml
dimensions:
  - name: order_month
    type: string
    sql: TO_CHAR(order_date, 'YYYY-MM')
    
  - name: order_year
    type: number
    sql: EXTRACT(YEAR FROM order_date)
    
  - name: quarter
    type: string
    sql: "'Q' || TO_CHAR(order_date, 'Q')"
```

### Hierarchical Queries

```yaml
datasets:
  org_hierarchy:
    source: oracle_db
    sql: |
      SELECT employee_id, manager_id, employee_name,
             LEVEL as hierarchy_level,
             SYS_CONNECT_BY_PATH(employee_name, '/') as path
      FROM employees
      START WITH manager_id IS NULL
      CONNECT BY PRIOR employee_id = manager_id
```

### Analytic Functions

```yaml
metrics:
  - name: running_total
    type: custom
    sql: SUM(amount) OVER (ORDER BY order_date)
    
  - name: percent_of_total
    type: custom
    sql: RATIO_TO_REPORT(SUM(amount)) OVER () * 100
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: oracle_db
    table: ANALYTICS.ORDERS
    
    dimensions:
      - name: order_id
        type: number
        sql: ORDER_ID
        primary_key: true
        
      - name: order_date
        type: date
        sql: ORDER_DATE
        
      - name: customer_id
        type: string
        sql: CUSTOMER_ID
        
      - name: region
        type: string
        sql: REGION
    
    metrics:
      - name: revenue
        type: sum
        sql: TOTAL_AMOUNT
        
      - name: order_count
        type: count
        sql: ORDER_ID
```

## Docker Setup

```yaml
version: '3.8'
services:
  oracle:
    image: gvenzl/oracle-xe:21-slim
    environment:
      - ORACLE_PASSWORD=oracle
    ports:
      - "1521:1521"
    volumes:
      - oracle_data:/opt/oracle/oradata

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - ORACLE_HOST=oracle
      - ORACLE_PORT=1521
      - ORACLE_SERVICE=XEPDB1
      - ORACLE_USER=analytics
      - ORACLE_PASSWORD=analytics

volumes:
  oracle_data:
```

## Troubleshooting

### ORA-12541: TNS:no listener
- Check Oracle listener is running
- Verify host and port

### ORA-01017: invalid username/password
- Verify credentials
- Check if password is case-sensitive

### Wallet Issues (Cloud)
- Download wallet from Oracle Cloud Console
- Extract to wallet_location path
- Set wallet_password correctly

