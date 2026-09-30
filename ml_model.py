import pickle, sqlite3
from pathlib import Path
from datetime import date
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from database import get_db
MODEL_PATH=Path(__file__).resolve().parent/'model.pkl'
FEATURES=['cpu_usage','memory_usage','temperature','disk_usage','uptime_hours','error_count','maintenance_count','failure_count','total_downtime','total_maintenance_cost','asset_age_days']

def feature_frame(user_id=None):
    conn=get_db(); where=''; args=()
    if user_id is not None: where='WHERE a.user_id=?'; args=(user_id,)
    sql=f'''SELECT a.asset_id,a.purchase_date, r.cpu_usage,r.memory_usage,r.temperature,r.disk_usage,r.uptime_hours,r.error_count,
    (SELECT COUNT(*) FROM maintenance_records m WHERE m.asset_id=a.asset_id) maintenance_count,
    (SELECT COUNT(*) FROM failure_records f WHERE f.asset_id=a.asset_id) failure_count,
    (SELECT COALESCE(SUM(downtime_hours),0) FROM maintenance_records m WHERE m.asset_id=a.asset_id) + (SELECT COALESCE(SUM(downtime_hours),0) FROM failure_records f WHERE f.asset_id=a.asset_id) total_downtime,
    (SELECT COALESCE(SUM(cost),0) FROM maintenance_records m WHERE m.asset_id=a.asset_id) total_maintenance_cost
    FROM assets a JOIN asset_readings r ON r.asset_id=a.asset_id {where}'''
    df=pd.read_sql_query(sql,conn,params=args); conn.close()
    if df.empty: return df
    df['asset_age_days']=((pd.Timestamp.today()-pd.to_datetime(df.purchase_date)).dt.days).clip(lower=0)
    df[FEATURES]=df[FEATURES].fillna(0); return df

def train_model():
    df=feature_frame()
    if len(df)<12: return {'ok':False,'message':'Insufficient data: at least 12 readings are required for a reliable academic split.'}
    df['target']=((df.failure_count>0) | (df.error_count>=8) | (df.temperature>=75)).astype(int)
    if df.target.nunique()<2: return {'ok':False,'message':'Insufficient data: training data has only one target class.'}
    X=df[FEATURES]; y=df.target
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.25,random_state=42,stratify=y)
    model=RandomForestClassifier(n_estimators=120,random_state=42,class_weight='balanced'); model.fit(Xtr,ytr)
    pred=model.predict(Xte); pickle.dump({'model':model,'features':FEATURES},open(MODEL_PATH,'wb'))
    return {'ok':True,'metrics':{'accuracy':accuracy_score(yte,pred),'precision':precision_score(yte,pred,zero_division=0),'recall':recall_score(yte,pred,zero_division=0),'f1':f1_score(yte,pred,zero_division=0),'confusion_matrix':confusion_matrix(yte,pred).tolist()},'rows':len(df)}

def risk_for_asset(asset_id):
    conn=get_db(); row=conn.execute('SELECT user_id FROM assets WHERE asset_id=?',(asset_id,)).fetchone(); conn.close()
    df=feature_frame(row['user_id'] if row else None); df=df[df.asset_id==asset_id]
    if df.empty: return {'level':'LOW','probability':0,'method':'Rule-based fallback','factors':['No readings available'],'action':'Add a current reading and schedule an inspection.'}
    r=df.iloc[-1]; factors=[]; score=0
    if r.temperature>=75: score+=30; factors.append('high temperature')
    if r.error_count>=8: score+=25; factors.append('high error count')
    if r.total_downtime>=20: score+=20; factors.append('high downtime')
    if r.failure_count>=2: score+=15; factors.append('repeated failures')
    if r.maintenance_count>=5: score+=10; factors.append('frequent maintenance')
    if MODEL_PATH.exists():
        try:
            bundle=pickle.load(open(MODEL_PATH,'rb')); x=r[FEATURES].to_frame().T; p=float(bundle['model'].predict_proba(x)[0][1]); level='HIGH' if p>=.66 else ('MEDIUM' if p>=.33 else 'LOW')
            return {'level':level,'probability':round(p*100,1),'method':'RandomForestClassifier','factors':factors or ['normal observed readings'],'action':'Schedule preventive maintenance and inspect the highlighted factors.' if level!='LOW' else 'Continue routine monitoring.'}
        except Exception: pass
    probability=min(score,100); level='HIGH' if probability>=66 else ('MEDIUM' if probability>=33 else 'LOW')
    return {'level':level,'probability':probability,'method':'Rule-based fallback','factors':factors or ['normal observed readings'],'action':'Schedule preventive maintenance and inspect the highlighted factors.' if level!='LOW' else 'Continue routine monitoring.'}
