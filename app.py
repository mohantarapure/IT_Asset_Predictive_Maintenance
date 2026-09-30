from flask import Flask, render_template, request, redirect, url_for, flash, session, g, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
import csv, io, json, sqlite3
from database import get_db, init_db
from analytics import analytics_for_user
from ml_model import train_model, risk_for_asset

app=Flask(__name__); app.secret_key='academic-project-secret-change-me'; init_db()

def login_required(f):
    @wraps(f)
    def w(*a,**kw):
        if not session.get('user_id'): flash('Please log in first.','warning'); return redirect(url_for('login'))
        return f(*a,**kw)
    return w
@app.context_processor
def inject(): return {'today':date.today().isoformat(),'user':g.get('user')}
@app.before_request
def load_user():
    g.user=None
    if session.get('user_id'):
        g.user=get_db().execute('SELECT * FROM users WHERE user_id=?',(session['user_id'],)).fetchone()
def owned(asset_id):
    return get_db().execute('SELECT * FROM assets WHERE asset_id=? AND user_id=?',(asset_id,session['user_id'])).fetchone()
def opts(conn): return {'categories':conn.execute('SELECT * FROM asset_categories ORDER BY category_name').fetchall(),'assets':conn.execute('SELECT asset_id,asset_name,asset_tag FROM assets WHERE user_id=? ORDER BY asset_name',(session['user_id'],)).fetchall()}

@app.route('/')
def index(): return redirect(url_for('dashboard' if session.get('user_id') else 'login'))
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip(); password=request.form.get('password','')
        if not name or not email or len(password)<6: flash('Name, email and a password of at least 6 characters are required.','danger')
        else:
            c=get_db()
            try: c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name,email,generate_password_hash(password))); c.commit(); flash('Registration successful. Please log in.','success'); return redirect(url_for('login'))
            except sqlite3.IntegrityError: flash('That email is already registered.','danger')
            finally: c.close()
    return render_template('auth.html',register=True)
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        c=get_db(); u=c.execute('SELECT * FROM users WHERE email=?',(request.form.get('email','').strip(),)).fetchone(); c.close()
        if u and check_password_hash(u['password'],request.form.get('password','')): session['user_id']=u['user_id']; return redirect(url_for('dashboard'))
        flash('Invalid email or password.','danger')
    return render_template('auth.html',register=False)
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    c=get_db(); uid=session['user_id']; cards=c.execute('''SELECT COUNT(*) total, SUM(status='Active') active, SUM(status='Under Maintenance') maintenance, SUM(status='Retired') retired, (SELECT COUNT(*) FROM maintenance_records m JOIN assets x ON x.asset_id=m.asset_id WHERE x.user_id=?) maint_count, (SELECT COUNT(*) FROM failure_records f JOIN assets x ON x.asset_id=f.asset_id WHERE x.user_id=?) failures, (SELECT COALESCE(SUM(m.cost),0) FROM maintenance_records m JOIN assets x ON x.asset_id=m.asset_id WHERE x.user_id=?) cost, (SELECT COALESCE(SUM(m.downtime_hours),0) FROM maintenance_records m JOIN assets x ON x.asset_id=m.asset_id WHERE x.user_id=?) downtime FROM assets WHERE user_id=?''',(uid,uid,uid,uid,uid)).fetchone(); upcoming=c.execute("SELECT COUNT(*) n FROM maintenance_schedule s JOIN assets a ON a.asset_id=s.asset_id WHERE a.user_id=? AND s.scheduled_date>=date('now') AND s.status!='Completed'",(uid,)).fetchone()['n']; cats=c.execute('SELECT c.category_name,COUNT(*) n FROM assets a JOIN asset_categories c ON c.category_id=a.category_id WHERE a.user_id=? GROUP BY c.category_id',(uid,)).fetchall(); statuses=c.execute('SELECT status,COUNT(*) n FROM assets WHERE user_id=? GROUP BY status',(uid,)).fetchall(); c.close(); return render_template('dashboard.html',cards=cards,upcoming=upcoming,cats=cats,statuses=statuses)

@app.route('/assets')
@login_required
def assets():
    c=get_db(); uid=session['user_id']; wh=['a.user_id=?']; args=[uid]
    for key,col in [('name','a.asset_name'),('tag','a.asset_tag'),('category','a.category_id'),('status','a.status'),('criticality','a.criticality'),('location','a.location')]:
        if request.args.get(key): wh.append(f'{col} LIKE ?' if key in ('name','tag','location') else f'{col}=?'); args.append('%'+request.args[key]+'%' if key in ('name','tag','location') else request.args[key])
    rows=c.execute('SELECT a.*,c.category_name FROM assets a JOIN asset_categories c ON c.category_id=a.category_id WHERE '+' AND '.join(wh)+' ORDER BY a.asset_id DESC',args).fetchall(); o=opts(c); c.close(); return render_template('assets.html',rows=rows,**o)
@app.route('/assets/add',methods=['GET','POST'])
@login_required
def add_asset():
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form
        try: c.execute('''INSERT INTO assets(user_id,category_id,asset_name,asset_tag,manufacturer,model,purchase_date,warranty_expiry,location,status,criticality,installation_date) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(session['user_id'],f['category_id'],f['asset_name'].strip(),f['asset_tag'].strip(),f.get('manufacturer',''),f.get('model',''),f['purchase_date'],f.get('warranty_expiry') or None,f['location'],f['status'],f['criticality'],f.get('installation_date') or None)); c.commit(); flash('Asset added.','success'); return redirect(url_for('assets'))
        except (sqlite3.IntegrityError,KeyError) as e: flash('Could not add asset: check required fields and unique asset tag.','danger')
    c.close(); return render_template('asset_form.html',asset=None,**o)
@app.route('/assets/<int:asset_id>/edit',methods=['GET','POST'])
@login_required
def edit_asset(asset_id):
    a=owned(asset_id)
    if not a: flash('Asset not found.','danger'); return redirect(url_for('assets'))
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form
        try: c.execute('''UPDATE assets SET category_id=?,asset_name=?,asset_tag=?,manufacturer=?,model=?,purchase_date=?,warranty_expiry=?,location=?,status=?,criticality=?,installation_date=? WHERE asset_id=? AND user_id=?''',(f['category_id'],f['asset_name'].strip(),f['asset_tag'].strip(),f.get('manufacturer',''),f.get('model',''),f['purchase_date'],f.get('warranty_expiry') or None,f['location'],f['status'],f['criticality'],f.get('installation_date') or None,asset_id,session['user_id'])); c.commit(); flash('Asset updated.','success'); return redirect(url_for('assets'))
        except sqlite3.IntegrityError: flash('Update failed; asset tag may already exist.','danger')
    c.close(); return render_template('asset_form.html',asset=a,**o)
@app.route('/assets/<int:asset_id>/delete',methods=['POST'])
@login_required
def delete_asset(asset_id):
    if not owned(asset_id): flash('Asset not found.','danger')
    else:
        c=get_db(); c.execute('DELETE FROM assets WHERE asset_id=? AND user_id=?',(asset_id,session['user_id'])); c.commit(); c.close(); flash('Asset deleted and logged by trigger.','success')
    return redirect(url_for('assets'))
@app.route('/assets/<int:asset_id>')
@login_required
def asset_detail(asset_id):
    a=owned(asset_id)
    if not a: return redirect(url_for('assets'))
    c=get_db(); m=c.execute('SELECT * FROM maintenance_records WHERE asset_id=? ORDER BY maintenance_date DESC',(asset_id,)).fetchall(); f=c.execute('SELECT * FROM failure_records WHERE asset_id=? ORDER BY failure_date DESC',(asset_id,)).fetchall(); r=c.execute('SELECT * FROM asset_readings WHERE asset_id=? ORDER BY reading_date DESC',(asset_id,)).fetchall(); totals=c.execute('SELECT COALESCE(SUM(cost),0) cost,COALESCE(SUM(downtime_hours),0) downtime FROM maintenance_records WHERE asset_id=?',(asset_id,)).fetchone(); c.close(); return render_template('asset_detail.html',asset=a,maintenance=m,failures=f,readings=r,totals=totals,risk=risk_for_asset(asset_id))

@app.route('/maintenance',methods=['GET','POST'])
@login_required
def maintenance():
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form
        try: c.execute('INSERT INTO maintenance_records(asset_id,maintenance_type,maintenance_date,description,technician,cost,downtime_hours,status) VALUES(?,?,?,?,?,?,?,?)',(f['asset_id'],f['maintenance_type'],f['maintenance_date'],f['description'],f['technician'],float(f['cost']),float(f['downtime_hours']),f['status'])); c.commit(); flash('Maintenance record added.','success')
        except (ValueError,sqlite3.IntegrityError): flash('Invalid maintenance values.','danger')
    wh='a.user_id=?'; args=[session['user_id']]
    if request.args.get('status'): wh+=' AND m.status=?'; args.append(request.args['status'])
    if request.args.get('type'): wh+=' AND m.maintenance_type=?'; args.append(request.args['type'])
    rows=c.execute('SELECT m.*,a.asset_name FROM maintenance_records m JOIN assets a ON a.asset_id=m.asset_id WHERE '+wh+' ORDER BY m.maintenance_date DESC',args).fetchall(); c.close(); return render_template('maintenance.html',rows=rows,**o)
@app.route('/maintenance/<int:id>/delete',methods=['POST'])
@login_required
def delete_maintenance(id):
    c=get_db(); c.execute('DELETE FROM maintenance_records WHERE maintenance_id=? AND asset_id IN (SELECT asset_id FROM assets WHERE user_id=?)',(id,session['user_id'])); c.commit(); c.close(); return redirect(url_for('maintenance'))

@app.route('/failures',methods=['GET','POST'])
@login_required
def failures():
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form
        try: c.execute('INSERT INTO failure_records(asset_id,failure_date,failure_type,severity,downtime_hours,repair_cost,description) VALUES(?,?,?,?,?,?,?)',(f['asset_id'],f['failure_date'],f['failure_type'],f['severity'],float(f['downtime_hours']),float(f['repair_cost']),f['description'])); c.commit(); flash('Failure record added.','success')
        except (ValueError,sqlite3.IntegrityError): flash('Invalid failure values.','danger')
    rows=c.execute('SELECT f.*,a.asset_name FROM failure_records f JOIN assets a ON a.asset_id=f.asset_id WHERE a.user_id=? ORDER BY f.failure_date DESC',(session['user_id'],)).fetchall(); c.close(); return render_template('failures.html',rows=rows,**o)
@app.route('/schedule',methods=['GET','POST'])
@login_required
def schedule():
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form; c.execute('INSERT INTO maintenance_schedule(asset_id,scheduled_date,maintenance_type,notes,status) VALUES(?,?,?,?,?)',(f['asset_id'],f['scheduled_date'],f['maintenance_type'],f.get('notes',''),f['status'])); c.commit(); flash('Schedule saved.','success')
    rows=c.execute('SELECT s.*,a.asset_name FROM maintenance_schedule s JOIN assets a ON a.asset_id=s.asset_id WHERE a.user_id=? ORDER BY s.scheduled_date',(session['user_id'],)).fetchall(); c.close(); return render_template('schedule.html',rows=rows,**o)
@app.route('/readings',methods=['GET','POST'])
@login_required
def readings():
    c=get_db(); o=opts(c)
    if request.method=='POST':
        f=request.form
        try: c.execute('INSERT INTO asset_readings(asset_id,reading_date,cpu_usage,memory_usage,temperature,disk_usage,uptime_hours,error_count) VALUES(?,?,?,?,?,?,?,?)',(f['asset_id'],f['reading_date'],float(f['cpu_usage']),float(f['memory_usage']),float(f['temperature']),float(f['disk_usage']),float(f['uptime_hours']),int(f['error_count']))); c.commit(); flash('Reading saved.','success')
        except (ValueError,sqlite3.IntegrityError): flash('Invalid reading values.','danger')
    rows=c.execute('SELECT r.*,a.asset_name FROM asset_readings r JOIN assets a ON a.asset_id=r.asset_id WHERE a.user_id=? ORDER BY r.reading_date DESC',(session['user_id'],)).fetchall(); c.close(); return render_template('readings.html',rows=rows,**o)

@app.route('/analytics')
@login_required
def analytics(): return render_template('analytics.html',data=analytics_for_user(session['user_id']),model=train_model())
@app.route('/masters',methods=['GET','POST'])
@login_required
def masters():
    c=get_db()
    if request.method=='POST':
        try: c.execute('INSERT INTO asset_categories(category_name) VALUES(?)',(request.form['category_name'].strip(),)); c.commit(); flash('Category added.','success')
        except sqlite3.IntegrityError: flash('Category already exists.','danger')
    cats=c.execute('SELECT c.*,COUNT(a.asset_id) used FROM asset_categories c LEFT JOIN assets a ON a.category_id=c.category_id GROUP BY c.category_id').fetchall(); c.close(); return render_template('masters.html',categories=cats)
@app.route('/masters/<int:id>/delete',methods=['POST'])
@login_required
def delete_master(id):
    c=get_db()
    try: c.execute('DELETE FROM asset_categories WHERE category_id=?',(id,)); c.commit(); flash('Category deleted.','success')
    except sqlite3.IntegrityError: flash('Cannot delete a category used by assets.','danger')
    c.close(); return redirect(url_for('masters'))
@app.route('/export/<kind>')
@login_required
def export(kind):
    tables={'assets':('SELECT a.asset_name,a.asset_tag,c.category_name,a.manufacturer,a.model,a.location,a.status,a.criticality FROM assets a JOIN asset_categories c ON c.category_id=a.category_id WHERE a.user_id=?','Asset List'),'maintenance':('SELECT m.*,a.asset_name FROM maintenance_records m JOIN assets a ON a.asset_id=m.asset_id WHERE a.user_id=?','Maintenance Records'),'failures':('SELECT f.*,a.asset_name FROM failure_records f JOIN assets a ON a.asset_id=f.asset_id WHERE a.user_id=?','Failure Records')}
    if kind not in tables: return 'Unknown export',404
    c=get_db(); rows=c.execute(tables[kind][0],(session['user_id'],)).fetchall(); c.close(); out=io.StringIO(); w=csv.writer(out); w.writerow(rows[0].keys() if rows else ['No records']); [w.writerow(tuple(r)) for r in rows]; return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={kind}.csv'})

if __name__=='__main__': app.run(debug=True)
