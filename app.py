# -*- coding: utf-8 -*-
import os, sqlite3, json, csv, io, hmac
from datetime import datetime, date
from pathlib import Path
import streamlit as st

TITLE = "SGAS | نظام تسيير ومتابعة المتربصين"
MAX_TRAINEES = 5000
DB = os.environ.get("SGAS_DB_PATH", "data/sgas_data.db")
Path(DB).parent.mkdir(parents=True, exist_ok=True)
st.set_page_config(page_title=TITLE, page_icon="🎓", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Cairo',sans-serif;direction:rtl}
.block-container{padding-top:1.2rem}
.hero{background:linear-gradient(120deg,#102f50,#1d527b);padding:22px 26px;border-radius:15px;color:white;margin-bottom:16px}
.hero h1{margin:0;font-weight:800}.hero p{margin:4px 0 0;color:#dceafa}
div[data-testid="stMetric"]{background:#f3f7fb;border:1px solid #dce6f1;padding:12px;border-radius:12px}
</style>""", unsafe_allow_html=True)

def db():
    c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS trainees(
        id TEXT PRIMARY KEY,name TEXT NOT NULL,group_no TEXT NOT NULL,wilaya TEXT NOT NULL,
        birth_date TEXT NOT NULL,created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS attendance(
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,trainee_id TEXT NOT NULL,
        attend_date TEXT NOT NULL,attend_time TEXT NOT NULL,slot TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('حاضر','غائب')),
        FOREIGN KEY(trainee_id) REFERENCES trainees(id) ON DELETE CASCADE,
        UNIQUE(trainee_id,attend_date,slot))""")
        c.execute("""CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,event_time TEXT NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL)""")

def q(sql,args=()):
    with db() as c: return c.execute(sql,args).fetchall()
def run(sql,args=()):
    with db() as c: return c.execute(sql,args)
def log(action,details=""):
    run("INSERT INTO logs(event_time,action,details) VALUES(?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),action,details))
def valid_date(s):
    try: datetime.strptime(str(s),"%Y-%m-%d"); return True
    except: return False
def backup_data():
    return {"format":"SGAS_BACKUP_V1","created_at":datetime.now().isoformat(timespec="seconds"),
      "trainees":[dict(x) for x in q("SELECT * FROM trainees")],
      "attendance":[dict(x) for x in q("SELECT * FROM attendance")],
      "logs":[dict(x) for x in q("SELECT * FROM logs")]}

init()
password=os.environ.get("SGAS_PASSWORD","")
if not password:
    st.error("لم تُضبط كلمة مرور المنصة. يجب إعداد SGAS_PASSWORD في إعدادات الاستضافة.")
    st.stop()
if not st.session_state.get("ok"):
    st.markdown('<div class="hero"><h1>SGAS</h1><p>نظام تسيير ومتابعة المتربصين | NEHARI.A</p></div>',unsafe_allow_html=True)
    with st.form("login"):
        p=st.text_input("كلمة المرور",type="password")
        submit=st.form_submit_button("دخول",use_container_width=True)
    if submit:
        if hmac.compare_digest(p,password): st.session_state.ok=True; st.rerun()
        else: st.error("كلمة المرور غير صحيحة")
    st.stop()

st.markdown('<div class="hero"><h1>SGAS</h1><p>نظام تسيير ومتابعة المتربصين | NEHARI.A</p></div>',unsafe_allow_html=True)
n=q("SELECT COUNT(*) n FROM trainees")[0]["n"]
a,b,c=st.columns(3)
a.metric("عدد المتربصين",f"{n} / {MAX_TRAINEES}")
b.metric("عدد الأفواج",len(q("SELECT DISTINCT group_no FROM trainees")))
c.metric("سجلات اليوم",q("SELECT COUNT(*) n FROM attendance WHERE attend_date=?",(date.today().isoformat(),))[0]["n"])
tabs=st.tabs(["المتربصون","الحضور والغياب","الأفواج","التقارير والتصدير","النسخ الاحتياطي","سجل العمليات"])

with tabs[0]:
    st.subheader("إدارة المتربصين")
    with st.expander("إضافة متربص",expanded=True):
        with st.form("add",clear_on_submit=True):
            x,y,z=st.columns(3); tid=x.text_input("رقم المتربص"); name=y.text_input("اسم ولقب المتربص"); group=z.text_input("رقم الفوج")
            x,y=st.columns(2); wilaya=x.text_input("ولاية المتربص"); birth=y.text_input("تاريخ الميلاد YYYY-MM-DD")
            add=st.form_submit_button("إضافة")
        if add:
            if not all(v.strip() for v in (tid,name,group,wilaya,birth)): st.error("املأ جميع الحقول")
            elif not valid_date(birth): st.error("تاريخ الميلاد غير صحيح")
            elif n>=MAX_TRAINEES: st.error("تم بلوغ سعة 5000 متربص")
            else:
                try:
                    run("INSERT INTO trainees VALUES(?,?,?,?,?,?)",(tid.strip(),name.strip(),group.strip(),wilaya.strip(),birth.strip(),datetime.now().isoformat(timespec="seconds")))
                    log("إضافة متربص",tid+" - "+name); st.success("تمت الإضافة"); st.rerun()
                except sqlite3.IntegrityError: st.error("رقم المتربص موجود مسبقاً")
    people=q("SELECT id,name,group_no,wilaya,birth_date FROM trainees ORDER BY group_no,name")
    search=st.text_input("بحث بالرقم أو الاسم أو الفوج أو الولاية")
    filtered=[r for r in people if search.lower() in " ".join(map(str,r)).lower()] if search else people
    st.dataframe([dict(r) for r in filtered],use_container_width=True,hide_index=True,
      column_config={"id":"رقم المتربص","name":"الاسم واللقب","group_no":"رقم الفوج","wilaya":"الولاية","birth_date":"تاريخ الميلاد"})
    if people:
        opts={f'{r["id"]} — {r["name"]}':r["id"] for r in people}
        label=st.selectbox("اختر متربصاً للتعديل أو الحذف",list(opts)); sid=opts[label]
        old=next(r for r in people if r["id"]==sid)
        with st.expander("تعديل بيانات المتربص"):
            with st.form("edit"):
                x,y,z=st.columns(3); ni=x.text_input("رقم المتربص",old["id"]); nn=y.text_input("الاسم",old["name"]); ng=z.text_input("الفوج",old["group_no"])
                x,y=st.columns(2); nw=x.text_input("الولاية",old["wilaya"]); nb=y.text_input("تاريخ الميلاد",old["birth_date"])
                save=st.form_submit_button("حفظ التعديل")
            if save:
                if not all(v.strip() for v in (ni,nn,ng,nw,nb)) or not valid_date(nb): st.error("تحقق من البيانات")
                else:
                    try:
                        with db() as con:
                            con.execute("UPDATE trainees SET id=?,name=?,group_no=?,wilaya=?,birth_date=? WHERE id=?",(ni,nn,ng,nw,nb,sid))
                            con.execute("UPDATE attendance SET trainee_id=? WHERE trainee_id=?",(ni,sid))
                        log("تعديل متربص",sid+" إلى "+ni); st.success("تم التعديل"); st.rerun()
                    except sqlite3.IntegrityError: st.error("رقم المتربص مستخدم")
        if st.button("حذف المتربص المحدد"):
            st.session_state.del_id=sid
        if st.session_state.get("del_id")==sid:
            st.warning("سيتم حذف المتربص وسجلات حضوره")
            yes,no=st.columns(2)
            if yes.button("تأكيد الحذف"):
                run("DELETE FROM attendance WHERE trainee_id=?",(sid,)); run("DELETE FROM trainees WHERE id=?",(sid,))
                log("حذف متربص",sid); st.session_state.pop("del_id",None); st.rerun()
            if no.button("إلغاء"): st.session_state.pop("del_id",None); st.rerun()

with tabs[1]:
    st.subheader("تسجيل الحضور والغياب")
    people=q("SELECT id,name,group_no FROM trainees ORDER BY group_no,name")
    if people:
        opts={f'{r["id"]} — {r["name"]} (الفوج {r["group_no"]})':r["id"] for r in people}
        with st.form("attendance"):
            x,y,z=st.columns(3); who=x.selectbox("المتربص",list(opts)); d=y.date_input("التاريخ",date.today()); t=z.time_input("الوقت",datetime.now().time().replace(second=0,microsecond=0))
            status=st.radio("الحالة",["حاضر","غائب"],horizontal=True)
            save=st.form_submit_button("تسجيل")
        if save:
            mins=t.hour*60+t.minute; slot=f"{(mins//30*30)//60:02d}:{(mins//30*30)%60:02d}"
            try:
                run("INSERT INTO attendance(trainee_id,attend_date,attend_time,slot,status) VALUES(?,?,?,?,?)",(opts[who],d.isoformat(),t.strftime("%H:%M"),slot,status))
                log("تسجيل "+status,f'{opts[who]} | {d} {t} | {slot}'); st.success("تم التسجيل"); st.rerun()
            except sqlite3.IntegrityError: st.warning("سبق تسجيل هذا المتربص في الفترة نفسها (30 دقيقة)")
    else: st.info("أضف المتربصين أولاً")
    st.caption("يسمح بالتسجيل المتكرر في اليوم، مرة واحدة لكل خانة زمنية من 30 دقيقة.")
    att=q("""SELECT a.record_id,a.attend_date,a.attend_time,a.slot,a.trainee_id,t.name,t.group_no,a.status
             FROM attendance a JOIN trainees t ON t.id=a.trainee_id ORDER BY a.attend_date DESC,a.attend_time DESC LIMIT 2000""")
    st.dataframe([dict(r) for r in att],use_container_width=True,hide_index=True)
    if att:
        choices={f'{r["attend_date"]} {r["attend_time"]} | {r["trainee_id"]} | {r["status"]}':r["record_id"] for r in att}
        chosen=st.selectbox("سجل الحضور المراد حذفه",list(choices))
        if st.button("حذف سجل الحضور"):
            run("DELETE FROM attendance WHERE record_id=?",(choices[chosen],)); log("حذف سجل حضور",chosen); st.rerun()

with tabs[2]:
    st.subheader("إحصائيات الأفواج")
    groups=q("""SELECT t.group_no,COUNT(DISTINCT t.id) trainee_count,
       SUM(CASE WHEN a.status='حاضر' THEN 1 ELSE 0 END) present_records,
       SUM(CASE WHEN a.status='غائب' THEN 1 ELSE 0 END) absent_records
       FROM trainees t LEFT JOIN attendance a ON t.id=a.trainee_id GROUP BY t.group_no ORDER BY t.group_no""")
    st.dataframe([dict(r) for r in groups],use_container_width=True,hide_index=True)
    st.caption("أعداد الحضور والغياب تمثل السجلات، وقد يتكرر الشخص في اليوم.")

with tabs[3]:
    st.subheader("التقارير")
    group_list=["الكل"]+[r["group_no"] for r in q("SELECT DISTINCT group_no FROM trainees ORDER BY group_no")]
    x,y=st.columns(2); rd=x.date_input("تاريخ التقرير",date.today()); rg=y.selectbox("الفوج",group_list)
    extra=" AND t.group_no=?" if rg!="الكل" else ""; args=[rd.isoformat()]+([rg] if extra else [])
    total=q("SELECT COUNT(*) n FROM trainees"+(" WHERE group_no=?" if extra else ""),([rg] if extra else []))[0]["n"]
    report=q("""SELECT a.attend_time,a.slot,t.id,t.name,t.group_no,a.status FROM attendance a
      JOIN trainees t ON t.id=a.trainee_id WHERE a.attend_date=?"""+extra+" ORDER BY a.slot,t.group_no,t.name",args)
    present=sum(r["status"]=="حاضر" for r in report); absent=sum(r["status"]=="غائب" for r in report)
    pct=present/(present+absent)*100 if present+absent else 0
    m1,m2,m3,m4=st.columns(4); m1.metric("إجمالي المتربصين",total); m2.metric("الحضور",present); m3.metric("الغياب",absent); m4.metric("نسبة الحضور",f"{pct:.1f}%")
    st.dataframe([dict(r) for r in report],use_container_width=True,hide_index=True)
    buf=io.StringIO(); w=csv.writer(buf); w.writerow(["التاريخ",rd.isoformat()]); w.writerow(["الفوج",rg]); w.writerow(["إجمالي المتربصين",total]); w.writerow(["الحضور",present]); w.writerow(["الغياب",absent]); w.writerow(["نسبة الحضور",f"{pct:.2f}%"]); w.writerow([]); w.writerow(["الوقت","الفترة","رقم المتربص","الاسم","الفوج","الحالة"])
    for r in report: w.writerow([r["attend_time"],r["slot"],r["id"],r["name"],r["group_no"],r["status"]])
    st.download_button("تنزيل تقرير CSV",buf.getvalue().encode("utf-8-sig"),f"SGAS_report_{rd}.csv","text/csv")
    buf2=io.StringIO(); w2=csv.writer(buf2); w2.writerow(["رقم المتربص","الاسم","الفوج","الولاية","تاريخ الميلاد"])
    for r in q("SELECT id,name,group_no,wilaya,birth_date FROM trainees ORDER BY group_no,name"): w2.writerow(list(r))
    st.download_button("تنزيل قائمة المتربصين CSV",buf2.getvalue().encode("utf-8-sig"),"SGAS_trainees.csv","text/csv")

with tabs[4]:
    st.subheader("النسخ الاحتياطي والاسترجاع")
    data=backup_data()
    st.download_button("تنزيل نسخة احتياطية JSON",json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8"),f"SGAS_backup_{date.today()}.json","application/json",use_container_width=True)
    upload=st.file_uploader("اختر نسخة JSON للاسترجاع",type=["json"])
    if upload:
        if st.button("استرجاع النسخة المحددة"):
            try:
                d=json.loads(upload.getvalue().decode("utf-8"))
                if d.get("format")!="SGAS_BACKUP_V1" or not all(isinstance(d.get(k),list) for k in ("trainees","attendance","logs")): raise ValueError("تنسيق غير صحيح")
                if len(d["trainees"])>MAX_TRAINEES: raise ValueError("تجاوز سعة 5000")
                ids=set()
                for t in d["trainees"]:
                    if not all(k in t for k in ("id","name","group_no","wilaya","birth_date","created_at")) or not valid_date(t["birth_date"]): raise ValueError("بيانات متربص غير صالحة")
                    if t["id"] in ids: raise ValueError("رقم متربص مكرر")
                    ids.add(t["id"])
                for a in d["attendance"]:
                    if a.get("trainee_id") not in ids or a.get("status") not in ("حاضر","غائب") or not valid_date(a.get("attend_date","")): raise ValueError("سجل حضور غير صالح")
                if not st.session_state.get("restore_confirm"):
                    st.session_state.restore_confirm=True; st.warning("اضغط الزر مرة ثانية لتأكيد استبدال البيانات الحالية.")
                else:
                    with db() as con:
                        con.execute("DELETE FROM attendance"); con.execute("DELETE FROM trainees"); con.execute("DELETE FROM logs")
                        for t in d["trainees"]: con.execute("INSERT INTO trainees VALUES(?,?,?,?,?,?)",(t["id"],t["name"],t["group_no"],t["wilaya"],t["birth_date"],t["created_at"]))
                        for a in d["attendance"]: con.execute("INSERT INTO attendance(record_id,trainee_id,attend_date,attend_time,slot,status) VALUES(?,?,?,?,?,?)",(a.get("record_id"),a["trainee_id"],a["attend_date"],a["attend_time"],a["slot"],a["status"]))
                        for l in d["logs"]: con.execute("INSERT INTO logs(id,event_time,action,details) VALUES(?,?,?,?)",(l.get("id"),l["event_time"],l["action"],l["details"]))
                    st.session_state.restore_confirm=False; log("استرجاع نسخة JSON",upload.name); st.success("تم الاسترجاع"); st.rerun()
            except Exception as e: st.session_state.restore_confirm=False; st.error(f"تعذر الاسترجاع: {e}")
    if st.button("تجهيز نسخة قاعدة SQLite"):
        with open(DB,"rb") as f: st.download_button("تنزيل ملف SQLite",f.read(),"sgas_data_backup.db","application/octet-stream")

with tabs[5]:
    st.subheader("سجل العمليات")
    logs=q("SELECT event_time,action,details FROM logs ORDER BY id DESC LIMIT 2000")
    st.dataframe([dict(r) for r in logs],use_container_width=True,hide_index=True)

st.divider()
st.caption("SGAS — NEHARI.A | احرص على النسخ الاحتياطي الدوري وحماية كلمة المرور.")
if st.button("تسجيل الخروج"):
    st.session_state.ok=False; st.rerun()
