-- Simplified Savings Plan scenario: one commitment per customer/hour.
-- OD-equivalent covered usage and utilization are computed before aggregation.
WITH eligible_usage AS (
    SELECT customer_id, usage_hour,
           SUM(on_demand_cost) AS baseline,
           SUM(CASE WHEN eligible = 1 THEN on_demand_cost ELSE 0 END) AS eligible_od
    FROM usage_hourly
    GROUP BY customer_id, usage_hour
), allocated AS (
    SELECT u.customer_id, u.usage_hour, u.baseline, u.eligible_od,
           c.committed_spend, c.discount_rate,
           CASE WHEN u.eligible_od < c.committed_spend / (1 - c.discount_rate)
                THEN u.eligible_od
                ELSE c.committed_spend / (1 - c.discount_rate) END AS covered_od
    FROM eligible_usage u
    JOIN commitments_hourly c
      ON u.customer_id = c.customer_id AND u.usage_hour = c.usage_hour
)
SELECT customer_id, usage_hour, baseline, eligible_od, covered_od,
       covered_od * (1 - discount_rate) AS applied_commitment,
       committed_spend,
       committed_spend - covered_od * (1 - discount_rate) AS unused_commitment,
       baseline - covered_od + committed_spend AS actual_cost,
       covered_od - committed_spend AS net_savings
FROM allocated
