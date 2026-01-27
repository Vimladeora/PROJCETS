### Smart Inventory Intelligence & Restock Automation System

import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3

### CONNECT TO DATABASE

conn = sqlite3.connect("inventory_system.db")
cursor = conn.cursor()

### LOAD DATA

products = pd.read_csv("products.csv")
inventory = pd.read_csv("inventory.csv")
demand = pd.read_csv("demand_history.csv")
sales = pd.read_csv("sales.csv")

inventory['manufacture_date'] = pd.to_datetime(inventory['manufacture_date'])
inventory['expiry_date'] = pd.to_datetime(inventory['expiry_date'])
demand['date'] = pd.to_datetime(demand['date'])
sales['sale_date'] = pd.to_datetime(sales['sale_date'])

today = datetime.today()


### 1. EXPIRY DAYS + STATUS

inventory['days_left'] = (inventory['expiry_date'] - today).dt.days

def expiry_status(x):
    if x <= 0:
        return "EXPIRED"
    elif x <= 2:
        return "URGENT"
    elif x <= 5:
        return "EXPIRING SOON"
    return "OK"

inventory['status'] = inventory['days_left'].apply(expiry_status)

### 2. DISCOUNT ENGINE

def discount_rule(days):
    if days <= 0:
        return 90
    elif days <= 2:
        return 60
    elif days <= 5:
        return 30
    return 0

inventory['discount_%'] = inventory['days_left'].apply(discount_rule)

### 3. DEMAND FORECAST (Simple ML logic)

forecast = demand.groupby("product_id")['daily_sold'].mean().rename("avg_daily_sales")

inventory = inventory.merge(forecast, on='product_id', how='left')
inventory['avg_daily_sales'] = inventory['avg_daily_sales'].fillna(0)

inventory['predicted_7day_demand'] = inventory['avg_daily_sales'] * 7

### 4. RESTOCK ENGINE

inventory['restock_flag'] = np.where(
    (inventory['quantity'] < inventory['predicted_7day_demand']) |
    (inventory['status'] == "URGENT"),
    True, False
)

inventory['restock_qty'] = np.where(
    inventory['restock_flag'],
    inventory['predicted_7day_demand'] - inventory['quantity'],
    0
)

inventory['restock_qty'] = inventory['restock_qty'].clip(lower=0)

### 5. ALERT SYSTEM

alerts = []
for _, row in inventory.iterrows():
    if row['status'] in ("URGENT", "EXPIRED"):
        alerts.append((row['product_id'], 'EXPIRY ALERT',
                       f"Product {row['product_id']} needs urgent action."))

    if row['restock_flag']:
        alerts.append((row['product_id'], 'RESTOCK ALERT',
                       f"Product {row['product_id']} needs restocking: {row['restock_qty']} units."))

alerts_df = pd.DataFrame(alerts, columns=['product_id', 'alert_type', 'message'])

### 6. LOAD INTO SQL TABLES

products.to_sql("products", conn, if_exists='replace', index=False)
inventory.to_sql("inventory", conn, if_exists='replace', index=False)
sales.to_sql("sales", conn, if_exists='replace', index=False)
alerts_df.to_sql("alerts", conn, if_exists='replace', index=False)

print("Data loaded successfully into SQLite database.")


### 7. ADVANCED SQL ANALYTICS (RUN INSIDE PYTHON)

# A) Expiry Loss
query_expiry_loss = """
WITH expiry_loss AS (
    SELECT
        i.product_id,
        SUM(i.quantity * p.price) AS expiry_loss_amount
    FROM inventory i
    JOIN products p ON i.product_id = p.product_id
    WHERE i.expiry_date < DATE('now')
    GROUP BY i.product_id
)
SELECT * FROM expiry_loss;
"""
expiry_loss_df = pd.read_sql_query(query_expiry_loss, conn)
print("\nExpiry Loss:\n", expiry_loss_df)

# B) Overstock vs Low Demand
query_overstock = """
WITH avg_sales AS (
    SELECT product_id, AVG(quantity_sold) AS avg_daily_sales
    FROM sales
    GROUP BY product_id
)
SELECT 
    i.product_id,
    i.quantity,
    s.avg_daily_sales,
    CASE
        WHEN s.avg_daily_sales < 2 AND i.quantity > 100 THEN 'OVERSTOCK ISSUE'
        WHEN s.avg_daily_sales >= 2 AND i.expiry_date < DATE('now') THEN 'SLOW MOVEMENT'
        ELSE 'NORMAL'
    END AS expiry_reason
FROM inventory i
LEFT JOIN avg_sales s
ON i.product_id = s.product_id;
"""
overstock_df = pd.read_sql_query(query_overstock, conn)
print("\nOverstock vs Demand:\n", overstock_df)

# C) Dead Stock
query_deadstock = """
SELECT 
    i.product_id,
    i.quantity
FROM inventory i
LEFT JOIN sales s
ON i.product_id = s.product_id
WHERE s.product_id IS NULL;
"""
deadstock_df = pd.read_sql_query(query_deadstock, conn)
print("\nDead Stock:\n", deadstock_df)

# D) Restock Priority
query_priority = """
WITH demand_calc AS (
    SELECT 
        product_id,
        AVG(quantity_sold) AS avg_sales
    FROM sales
    GROUP BY product_id
)
SELECT 
    i.product_id,
    i.quantity,
    d.avg_sales,
    DENSE_RANK() OVER (ORDER BY d.avg_sales DESC) AS restock_priority
FROM inventory i
JOIN demand_calc d
ON i.product_id = d.product_id;
"""
priority_df = pd.read_sql_query(query_priority, conn)
print("\nRestock Priority:\n", priority_df)

# E) Category Level Loss
query_category_loss = """
SELECT 
    p.category,
    SUM(i.quantity * p.price) AS total_expiry_loss
FROM inventory i
JOIN products p ON i.product_id = p.product_id
WHERE i.expiry_date < DATE('now')
GROUP BY p.category
ORDER BY total_expiry_loss DESC;
"""
category_loss_df = pd.read_sql_query(query_category_loss, conn)
print("\nCategory Loss:\n", category_loss_df)
