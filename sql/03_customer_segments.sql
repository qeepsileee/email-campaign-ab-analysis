SELECT
    channel,
    newbie,
    segment,
    COUNT(*) AS customers,
    SUM(conversion) AS buyers,
    AVG(conversion * 1.0) AS conversion_rate,
    AVG(spend) AS revenue_per_customer
FROM customers
GROUP BY channel, newbie, segment
ORDER BY channel, newbie, segment;
