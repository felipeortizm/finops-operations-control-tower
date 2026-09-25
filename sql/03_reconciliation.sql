-- Signed variance: positive means expected fee exceeds billed fee.
SELECT p.customer_id, p.customer_name, p.expected_fee,
       b.invoice_id, b.billed_fee, b.payment_status,
       CASE WHEN b.invoice_id IS NULL THEN 'Missing invoice'
            WHEN ABS(p.expected_fee - b.billed_fee) > 0.01 THEN 'Mismatch'
            ELSE 'Matched' END AS reconciliation_status,
       ROUND(p.expected_fee - COALESCE(b.billed_fee, 0), 2) AS variance
FROM portfolio_metrics p
LEFT JOIN marketplace_billing b
  ON b.customer_id = p.customer_id AND b.billing_month = :billing_month
ORDER BY ABS(p.expected_fee - COALESCE(b.billed_fee, 0)) DESC
