-- The app creates the hourly_metrics view from 01_hourly_metrics.sql.
SELECT c.customer_id, c.customer_name, c.fee_rate,
       SUM(h.baseline) AS baseline,
       SUM(h.eligible_od) AS eligible_od,
       SUM(h.covered_od) AS covered_od,
       SUM(h.applied_commitment) AS applied_commitment,
       SUM(h.committed_spend) AS committed_spend,
       SUM(h.unused_commitment) AS unused_commitment,
       SUM(h.actual_cost) AS actual_cost,
       SUM(h.net_savings) AS net_savings,
       CASE WHEN SUM(h.eligible_od) > 0
            THEN SUM(h.covered_od) / SUM(h.eligible_od) ELSE 0 END AS coverage,
       CASE WHEN SUM(h.committed_spend) > 0
            THEN SUM(h.applied_commitment) / SUM(h.committed_spend) ELSE 0 END AS utilization,
       ROUND(CASE WHEN SUM(h.net_savings) > 0
                  THEN SUM(h.net_savings) * c.fee_rate ELSE 0 END, 2) AS expected_fee
FROM hourly_metrics h JOIN customers c ON c.customer_id = h.customer_id
GROUP BY c.customer_id, c.customer_name, c.fee_rate
ORDER BY c.customer_name
