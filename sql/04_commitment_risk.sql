-- Compare the last seven days of the sample with the previous seven.
WITH period_metrics AS (
    SELECT customer_id,
           CASE WHEN usage_hour >= :cutoff THEN 'recent' ELSE 'previous' END AS period,
           SUM(eligible_od) AS eligible_od,
           SUM(applied_commitment) AS applied_commitment,
           SUM(committed_spend) AS committed_spend,
           SUM(unused_commitment) AS unused_commitment
    FROM hourly_metrics
    GROUP BY customer_id, CASE WHEN usage_hour >= :cutoff THEN 'recent' ELSE 'previous' END
), compared AS (
    SELECT c.customer_id, c.customer_name,
           MAX(CASE WHEN p.period = 'recent' THEN p.eligible_od END) AS recent_eligible,
           MAX(CASE WHEN p.period = 'previous' THEN p.eligible_od END) AS previous_eligible,
           MAX(CASE WHEN p.period = 'recent' THEN p.applied_commitment END) AS applied,
           MAX(CASE WHEN p.period = 'recent' THEN p.committed_spend END) AS committed,
           MAX(CASE WHEN p.period = 'recent' THEN p.unused_commitment END) AS unused
    FROM customers c JOIN period_metrics p ON c.customer_id = p.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT *, CASE WHEN committed > 0 THEN applied / committed ELSE 0 END AS recent_utilization,
       CASE WHEN previous_eligible > 0
            THEN recent_eligible / previous_eligible - 1 ELSE 0 END AS usage_change
FROM compared
ORDER BY recent_utilization ASC
