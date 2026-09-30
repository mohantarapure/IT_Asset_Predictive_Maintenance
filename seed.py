from datetime import date,timedelta
from werkzeug.security import generate_password_hash
from database import get_db,init_db

def seed():
 init_db(); c=get_db(); c.executescript('DELETE FROM deleted_asset_log; DELETE FROM asset_readings; DELETE FROM maintenance_schedule; DELETE FROM failure_records; DELETE FROM maintenance_records; DELETE FROM assets; DELETE FROM asset_categories; DELETE FROM users;')
 uid=c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",('Demo User','demo@example.com',generate_password_hash('demo123'))).lastrowid
 c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",('Second Demo','student@example.com',generate_password_hash('student123')))
 cats=['Laptop','Desktop','Server','Router','Switch','Printer','UPS','Storage']; c.executemany('INSERT INTO asset_categories(category_name) VALUES(?)',[(x,) for x in cats]); cat={r['category_name']:r['category_id'] for r in c.execute('SELECT * FROM asset_categories')}
 specs=[('Server-001','SRV-001','Server','Dell','PowerEdge R740','Data Center','High'),('Server-002','SRV-002','Server','HP','ProLiant DL380','Data Center','High'),('Router-001','RTR-001','Router','Cisco','ISR 4331','Network Room','High'),('Switch-001','SWT-001','Switch','Cisco','Catalyst 9200','Network Room','Medium'),('Laptop-001','LAP-001','Laptop','Lenovo','ThinkPad E14','Admin Office','Low'),('Laptop-002','LAP-002','Laptop','HP','ProBook 440','Lab A','Low'),('Desktop-001','DTP-001','Desktop','Dell','OptiPlex 7090','Lab A','Medium'),('Printer-001','PRN-001','Printer','Canon','Laser 2000','Admin Office','Low'),('UPS-001','UPS-001','UPS','APC','Smart-UPS','Data Center','High'),('Storage-001','STR-001','Storage','Synology','RS1221+','Data Center','High'),('Laptop-003','LAP-003','Laptop','Acer','TravelMate','Lab B','Low'),('Desktop-002','DTP-002','Desktop','HP','ProDesk 600','Lab B','Medium')]
 assets=[]
 for i,(name,tag,catn,mfg,model,loc,crit) in enumerate(specs):
  pd=(date.today()-timedelta(days=300+i*70)).isoformat(); wd=(date.today()+timedelta(days=180-i*10)).isoformat(); status='Under Maintenance' if i in (1,8) else ('Retired' if i==10 else 'Active')
  aid=c.execute('INSERT INTO assets(user_id,category_id,asset_name,asset_tag,manufacturer,model,purchase_date,warranty_expiry,location,status,criticality,installation_date) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(uid,cat[catn],name,tag,mfg,model,pd,wd,loc,status,crit,pd)).lastrowid; assets.append(aid)
 for i,aid in enumerate(assets):
  for j in range(2+(i%2)):
   d=(date.today()-timedelta(days=20+j*45+i)).isoformat(); c.execute('INSERT INTO maintenance_records(asset_id,maintenance_type,maintenance_date,description,technician,cost,downtime_hours,status) VALUES(?,?,?,?,?,?,?,?)',(aid,['Preventive','Corrective','Emergency'][(i+j)%3],d,'Routine inspection and component check','Tech '+str((i%3)+1),round(120+(i*37)+(j*55),2),round(1.5+(i%4)*2+j,1),'Completed'))
  if i%2==0:
   d=(date.today()-timedelta(days=35+i*3)).isoformat(); c.execute('INSERT INTO failure_records(asset_id,failure_date,failure_type,severity,downtime_hours,repair_cost,description) VALUES(?,?,?,?,?,?,?)',(aid,d,'Overheating' if i%3==0 else 'Network fault',['Medium','High','Critical'][i%3],4+i%5,300+i*42,'Observed during operations'))
  for j in range(2):
   d=(date.today()-timedelta(days=j*14+i)).isoformat(); c.execute('INSERT INTO asset_readings(asset_id,reading_date,cpu_usage,memory_usage,temperature,disk_usage,uptime_hours,error_count) VALUES(?,?,?,?,?,?,?,?)',(aid,d,45+i*3+j*4,50+i*2,58+i*2+j*8,55+i,120+i*14,2+i%7+j*4))
  c.execute('INSERT INTO maintenance_schedule(asset_id,scheduled_date,maintenance_type,notes,status) VALUES(?,?,?,?,?)',(aid,(date.today()+timedelta(days=7+i)).isoformat(),'Preventive','Inspect readings and clean components','Scheduled' if i%3 else 'Pending'))
 c.commit(); c.close(); print('Seeded demo data.')
if __name__=='__main__': seed()
