-- SQLite demonstration queries for IT Asset PM
-- 1 SELECT / WHERE / ORDER BY
SELECT * FROM assets WHERE status='Active' ORDER BY purchase_date;
-- 2 LIKE
SELECT * FROM assets WHERE asset_name LIKE '%Server%';
-- 3 BETWEEN
SELECT * FROM maintenance_records WHERE cost BETWEEN 100 AND 500;
-- 4 COUNT
SELECT COUNT(*) AS total_assets FROM assets;
-- 5 SUM
SELECT SUM(cost) AS total_maintenance_cost FROM maintenance_records;
-- 6 AVG, MIN, MAX
SELECT AVG(cost) average_cost, MIN(cost) minimum_cost, MAX(cost) maximum_cost FROM maintenance_records;
-- 7 GROUP BY
SELECT status, COUNT(*) AS asset_count FROM assets GROUP BY status;
-- 8 HAVING
SELECT asset_id, SUM(cost) cost FROM maintenance_records GROUP BY asset_id HAVING SUM(cost)>500;
-- 9 INNER JOIN
SELECT a.asset_name,c.category_name FROM assets a INNER JOIN asset_categories c ON a.category_id=c.category_id;
-- 10 LEFT JOIN
SELECT a.asset_name,COUNT(m.maintenance_id) records FROM assets a LEFT JOIN maintenance_records m ON a.asset_id=m.asset_id GROUP BY a.asset_id;
-- 11 subquery
SELECT * FROM assets WHERE asset_id IN (SELECT asset_id FROM failure_records GROUP BY asset_id HAVING COUNT(*)>0);
-- 12 date filtering
SELECT * FROM maintenance_records WHERE maintenance_date BETWEEN date('now','-90 day') AND date('now');
-- 13 maintenance cost by category
SELECT c.category_name,SUM(m.cost) total_cost FROM asset_categories c JOIN assets a ON a.category_id=c.category_id JOIN maintenance_records m ON m.asset_id=a.asset_id GROUP BY c.category_id ORDER BY total_cost DESC;
-- 14 failure analysis
SELECT severity,COUNT(*) failures,SUM(downtime_hours) downtime FROM failure_records GROUP BY severity ORDER BY failures DESC;
-- 15 monthly maintenance cost
SELECT substr(maintenance_date,1,7) month,SUM(cost) cost FROM maintenance_records GROUP BY month ORDER BY month;
-- 16 view
SELECT * FROM asset_maintenance_summary ORDER BY total_maintenance_cost DESC;
-- 17 correlated subquery: assets above average cost
SELECT a.asset_name FROM assets a WHERE (SELECT COALESCE(SUM(cost),0) FROM maintenance_records m WHERE m.asset_id=a.asset_id) > (SELECT AVG(cost) FROM maintenance_records);
-- 18 highest downtime
SELECT a.asset_name,SUM(m.downtime_hours) downtime FROM assets a JOIN maintenance_records m ON m.asset_id=a.asset_id GROUP BY a.asset_id ORDER BY downtime DESC LIMIT 5;
