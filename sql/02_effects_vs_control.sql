WITH metrics AS (
    SELECT
        segment,
        COUNT(*) AS customers,
        AVG(conversion * 1.0) AS conversion_rate,
        AVG(visit * 1.0) AS visit_rate,
        AVG(spend) AS revenue_per_customer
    FROM customers
    GROUP BY segment
), control AS (
    SELECT * FROM metrics WHERE segment = 'No E-Mail'
)
SELECT
    m.segment,
    m.conversion_rate - c.conversion_rate AS conversion_effect,
    m.conversion_rate / c.conversion_rate - 1 AS conversion_relative_lift,
    m.visit_rate - c.visit_rate AS visit_effect,
    m.revenue_per_customer - c.revenue_per_customer AS revenue_effect
FROM metrics m
CROSS JOIN control c
WHERE m.segment <> 'No E-Mail';
