-- ACADEMIC REFERENCE ONLY. The running application uses SQLite.
CREATE DATABASE it_asset_maintenance;
USE it_asset_maintenance;
CREATE TABLE users(user_id INT PRIMARY KEY AUTO_INCREMENT,name VARCHAR(100) NOT NULL,email VARCHAR(150) UNIQUE NOT NULL,password VARCHAR(255) NOT NULL);
CREATE TABLE assets(asset_id INT PRIMARY KEY AUTO_INCREMENT,user_id INT,category_id INT,asset_tag VARCHAR(50) UNIQUE NOT NULL,FOREIGN KEY(user_id) REFERENCES users(user_id),FOREIGN KEY(category_id) REFERENCES asset_categories(category_id));
-- Example JOIN, GROUP BY, HAVING:
SELECT c.category_name,COUNT(a.asset_id) total_assets FROM asset_categories c LEFT JOIN assets a ON a.category_id=c.category_id GROUP BY c.category_id HAVING COUNT(a.asset_id)>0;
-- Example VIEW:
CREATE VIEW asset_summary AS SELECT asset_id,asset_tag,status FROM assets;
-- Example TRIGGER:
CREATE TRIGGER audit_asset_delete AFTER DELETE ON assets FOR EACH ROW INSERT INTO deleted_asset_log(asset_id,asset_tag) VALUES(OLD.asset_id,OLD.asset_tag);
-- MySQL stored procedure/function syntax (not run by SQLite):
DELIMITER //
CREATE PROCEDURE assets_by_status(IN p_status VARCHAR(40)) BEGIN SELECT * FROM assets WHERE status=p_status; END//
CREATE FUNCTION maintenance_total(p_asset INT) RETURNS DECIMAL(10,2) DETERMINISTIC RETURN (SELECT COALESCE(SUM(cost),0) FROM maintenance_records WHERE asset_id=p_asset)//
DELIMITER ;
-- Running application uses SQLite. This file is academic DBMS reference only.
