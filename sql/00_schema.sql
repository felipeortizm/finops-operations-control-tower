CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(80) NOT NULL UNIQUE,
    fee_rate NUMERIC(6,4) NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_hourly (
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    usage_hour VARCHAR(19) NOT NULL,
    service VARCHAR(30) NOT NULL,
    on_demand_cost NUMERIC(14,2) NOT NULL,
    eligible INTEGER NOT NULL,
    PRIMARY KEY (customer_id, usage_hour, service)
);

CREATE TABLE IF NOT EXISTS commitments_hourly (
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    usage_hour VARCHAR(19) NOT NULL,
    committed_spend NUMERIC(14,2) NOT NULL,
    discount_rate NUMERIC(6,4) NOT NULL,
    PRIMARY KEY (customer_id, usage_hour)
);

CREATE TABLE IF NOT EXISTS marketplace_billing (
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    billing_month VARCHAR(7) NOT NULL,
    invoice_id VARCHAR(60) NOT NULL UNIQUE,
    billed_fee NUMERIC(14,2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL,
    PRIMARY KEY (customer_id, billing_month)
);
