# MySQL

Connect to MySQL and MariaDB databases.

---

## Requirements

- MySQL 5.7+ or MariaDB 10.2+
- Network access from connector
- User with SELECT permissions

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mysql-prod",
    "type": "mysql",
    "connection": {
      "host": "db.example.com",
      "port": 3306,
      "database": "analytics",
      "user": "bi_readonly",
      "password": "your-password",
      "ssl_mode": "REQUIRED"
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | Database hostname | Required |
| `port` | Database port | `3306` |
| `database` | Database name | Required |
| `user` | Username | Required |
| `password` | Password | Required |
| `ssl_mode` | SSL mode | `PREFERRED` |
| `charset` | Character set | `utf8mb4` |

### SSL Modes

| Mode | Description |
|------|-------------|
| `DISABLED` | No SSL |
| `PREFERRED` | Use SSL if available |
| `REQUIRED` | Require SSL |
| `VERIFY_CA` | Verify server certificate |
| `VERIFY_IDENTITY` | Verify certificate + hostname |

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: mysql-prod
    table: orders
    
    dimensions:
      - name: region
        type: string
        expr: region
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
```

---

## Database Setup

### Create Read-Only User

```sql
-- Create user
CREATE USER 'bi_readonly'@'%' IDENTIFIED BY 'secure-password';

-- Grant select on database
GRANT SELECT ON analytics.* TO 'bi_readonly'@'%';

-- Apply changes
FLUSH PRIVILEGES;
```

### Enable Remote Access

Edit `my.cnf`:

```ini
[mysqld]
bind-address = 0.0.0.0
```

---

## MariaDB

The MySQL adapter works with MariaDB:

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mariadb-prod",
    "type": "mariadb",
    "connection": {
      "host": "mariadb.example.com",
      "port": 3306,
      "database": "analytics",
      "user": "bi_readonly",
      "password": "your-password"
    }
  }'
```

---

## Troubleshooting

### Connection Refused

```
Can't connect to MySQL server on 'host' (111)
```

**Solutions**:
1. Verify MySQL is running
2. Check `bind-address` allows connections
3. Check firewall rules
4. Verify port number

### Access Denied

```
Access denied for user 'bi_readonly'@'host'
```

**Solutions**:
1. Verify username and password
2. Check user host restrictions (`%` for any host)
3. Verify GRANT privileges

