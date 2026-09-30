import pandas as pd
from database import get_db

def analytics_for_user(user_id):
    conn=get_db()
    q=lambda sql, args=(): pd.read_sql_query(sql, conn, params=args)
    summary=q('''SELECT COALESCE(SUM(m.cost),0) total_cost, COALESCE(AVG(m.cost),0) average_cost, COALESCE(MAX(m.cost),0) max_cost, COALESCE(MIN(m.cost),0) min_cost, COALESCE(SUM(m.downtime_hours),0) total_downtime, COALESCE(AVG(m.downtime_hours),0) average_downtime, COUNT(m.maintenance_id) maintenance_count, COUNT(f.failure_id) failure_count FROM assets a LEFT JOIN maintenance_records m ON m.asset_id=a.asset_id LEFT JOIN failure_records f ON f.asset_id=a.asset_id WHERE a.user_id=?''',(user_id,)).iloc[0].to_dict()
    by_category=q('''SELECT c.category_name, COUNT(DISTINCT a.asset_id) assets, COUNT(DISTINCT f.failure_id) failures, COALESCE(SUM(m.cost),0) maintenance_cost FROM assets a JOIN asset_categories c ON c.category_id=a.category_id LEFT JOIN maintenance_records m ON m.asset_id=a.asset_id LEFT JOIN failure_records f ON f.asset_id=a.asset_id WHERE a.user_id=? GROUP BY c.category_id ORDER BY maintenance_cost DESC''',(user_id,)).to_dict('records')
    by_month=q('''SELECT substr(m.maintenance_date,1,7) month, SUM(m.cost) cost, SUM(m.downtime_hours) downtime FROM maintenance_records m JOIN assets a ON a.asset_id=m.asset_id WHERE a.user_id=? GROUP BY month ORDER BY month''',(user_id,)).to_dict('records')
    failures_month=q('''SELECT substr(f.failure_date,1,7) month, COUNT(*) count FROM failure_records f JOIN assets a ON a.asset_id=f.asset_id WHERE a.user_id=? GROUP BY month ORDER BY month''',(user_id,)).to_dict('records')
    top=q('''SELECT a.asset_name,a.asset_tag,COUNT(DISTINCT f.failure_id) failure_count,COALESCE(SUM(m.cost),0) maintenance_cost,COALESCE(SUM(m.downtime_hours),0) downtime FROM assets a LEFT JOIN maintenance_records m ON m.asset_id=a.asset_id LEFT JOIN failure_records f ON f.asset_id=a.asset_id WHERE a.user_id=? GROUP BY a.asset_id ORDER BY maintenance_cost DESC''',(user_id,)).to_dict('records')
    conn.close(); return {'summary':summary,'by_category':by_category,'by_month':by_month,'failures_month':failures_month,'top_assets':top}
