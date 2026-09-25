-- Operational checks are also enforced in src/operations.py.
SELECT 'missing commitment hour' AS issue, COUNT(*) AS affected_rows
FROM (SELECT DISTINCT customer_id, usage_hour FROM usage_hourly) u
LEFT JOIN commitments_hourly c
  ON c.customer_id = u.customer_id AND c.usage_hour = u.usage_hour
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'invalid cost or eligibility', COUNT(*) FROM usage_hourly
WHERE on_demand_cost < 0 OR eligible NOT IN (0,1)
UNION ALL
SELECT 'invalid commitment or discount', COUNT(*) FROM commitments_hourly
WHERE committed_spend < 0 OR discount_rate < 0 OR discount_rate >= 1
