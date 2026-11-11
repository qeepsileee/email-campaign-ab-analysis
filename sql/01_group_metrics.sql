SELECT
    segment,
    COUNT(*) AS customers,
    SUM(visit) AS visitors,
    SUM(conversion) AS buyers,
    SUM(spend) AS revenue,
    AVG(visit * 1.0) AS visit_rate,
    AVG(conversion * 1.0) AS conversion_rate,
    AVG(spend) AS revenue_per_customer
FROM customers
GROUP BY segment
ORDER BY segment;
