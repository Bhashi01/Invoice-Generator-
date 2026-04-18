"""
Trainer Invoice Automation - Streamlit Version
Deploy to: streamlit.io/cloud (free, instant hosting)

Run locally: streamlit run app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO
import os

# Import the PDF generator
from invoice_generator import generate_invoice, amount_words

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trainer Invoice Automation",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "invoices.db"
BILLED_TO = {
    "name": "Metis Eduventures Private Limited",
    "address": "2nd floor, 207A-208, Tower A, Unitech Cyber Park, Sec-39 Gurgaon, Haryana - 122001",
    "gstin": "06AAHCM7263M1ZZ"
}

# ── Database Functions ────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS trainers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        pan TEXT,
        gstin TEXT DEFAULT 'NA',
        rate_per_hour REAL NOT NULL,
        account_holder TEXT,
        account_number TEXT,
        ifsc TEXT,
        account_type TEXT DEFAULT 'Savings Account',
        bank_name TEXT
    );
    
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_id INTEGER NOT NULL,
        college TEXT NOT NULL,
        session_date TEXT NOT NULL,
        hours REAL NOT NULL,
        students INTEGER DEFAULT 0,
        topic TEXT,
        program_name TEXT,
        po_number TEXT,
        FOREIGN KEY (trainer_id) REFERENCES trainers(id)
    );
    
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        trainer_id INTEGER NOT NULL,
        invoice_month TEXT NOT NULL,
        total REAL NOT NULL,
        net_payable REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trainer_id) REFERENCES trainers(id)
    );
    """)
    conn.commit()
    conn.close()

def get_trainers():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM trainers ORDER BY name", conn)
    conn.close()
    return df

def add_trainer(data):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT INTO trainers 
        (name, email, phone, address, pan, gstin, rate_per_hour,
         account_holder, account_number, ifsc, account_type, bank_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (data['name'], data['email'], data['phone'], data['address'],
          data['pan'], data['gstin'], data['rate_per_hour'],
          data['account_holder'], data['account_number'], data['ifsc'],
          data['account_type'], data['bank_name']))
    conn.commit()
    conn.close()

def delete_trainer(tid):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM trainers WHERE id=?", (tid,))
    conn.commit()
    conn.close()

def get_sessions(trainer_id=None, month=None):
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT s.*, t.name as trainer_name, t.rate_per_hour
        FROM sessions s
        JOIN trainers t ON s.trainer_id = t.id
        WHERE 1=1
    """
    params = []
    if trainer_id:
        query += " AND s.trainer_id = ?"
        params.append(trainer_id)
    if month:
        query += " AND s.session_date LIKE ?"
        params.append(f"{month}%")
    query += " ORDER BY s.session_date DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def add_session(data):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT INTO sessions
        (trainer_id, college, session_date, hours, students, topic, program_name, po_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data['trainer_id'], data['college'], data['session_date'],
          data['hours'], data['students'], data['topic'],
          data['program_name'], data['po_number']))
    conn.commit()
    conn.close()

def delete_session(sid):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
    conn.commit()
    conn.close()

def get_next_invoice_number():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute("SELECT COUNT(*) FROM invoices")
    count = cur.fetchone()[0]
    conn.close()
    return f"INV-{count + 1:04d}"

def save_invoice_record(inv_num, trainer_id, month, total, net):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT INTO invoices (invoice_number, trainer_id, invoice_month, total, net_payable)
        VALUES (?, ?, ?, ?, ?)
    """, (inv_num, trainer_id, month, total, net))
    conn.commit()
    conn.close()

# ── Helper Functions ──────────────────────────────────────────────────────────
def ordinal(d):
    if 10 <= d % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
    return f"{d:02d}{suf}"

def format_dates(date_strs):
    if not date_strs:
        return ""
    ds = sorted([datetime.strptime(d, "%Y-%m-%d") for d in date_strs])
    if len(ds) == 1:
        d = ds[0]
        return f"{ordinal(d.day)} {d.strftime('%b')}"
    first, last = ds[0], ds[-1]
    if first.month == last.month:
        return f"{ordinal(first.day)} {first.strftime('%b')} - {ordinal(last.day)} {last.strftime('%b')}"
    return ", ".join(f"{ordinal(d.day)} {d.strftime('%b')}" for d in ds)

# ── UI Components ─────────────────────────────────────────────────────────────
def show_dashboard():
    st.title("📊 Dashboard")
    
    conn = sqlite3.connect(DB_FILE)
    trainers_count = conn.execute("SELECT COUNT(*) FROM trainers").fetchone()[0]
    sessions_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    invoices_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    total_paid = conn.execute("SELECT COALESCE(SUM(net_payable), 0) FROM invoices").fetchone()[0]
    
    this_month = datetime.now().strftime("%Y-%m")
    month_sessions = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_date LIKE ?",
        (f"{this_month}%",)
    ).fetchone()[0]
    conn.close()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Trainers", trainers_count)
    col2.metric("Sessions This Month", month_sessions)
    col3.metric("Total Sessions", sessions_count)
    col4.metric("Invoices Generated", invoices_count)
    col5.metric("Total Paid Out", f"₹{total_paid:,.0f}")
    
    st.subheader("Recent Invoices")
    conn = sqlite3.connect(DB_FILE)
    recent = pd.read_sql_query("""
        SELECT i.invoice_number, t.name as trainer, i.invoice_month,
               i.total, i.net_payable, i.created_at
        FROM invoices i
        JOIN trainers t ON i.trainer_id = t.id
        ORDER BY i.created_at DESC
        LIMIT 10
    """, conn)
    conn.close()
    
    if len(recent) > 0:
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("No invoices generated yet. Add trainers and sessions to get started!")

def show_trainers():
    st.title("👥 Trainers")
    
    trainers = get_trainers()
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add Trainer", type="primary", use_container_width=True):
            st.session_state.show_add_trainer = True
    
    if st.session_state.get('show_add_trainer', False):
        with st.form("add_trainer_form"):
            st.subheader("Add New Trainer")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *", placeholder="e.g. Ramesh Kumar")
                email = st.text_input("Email", placeholder="ramesh@example.com")
                phone = st.text_input("Phone", placeholder="9876543210")
                pan = st.text_input("PAN", placeholder="ABCDE1234F")
            
            with col2:
                rate = st.number_input("Hourly Rate (₹) *", min_value=0, value=1500, step=100)
                gstin = st.text_input("GSTIN", value="NA", placeholder="22ABCDE1234F1Z5")
                account_holder = st.text_input("Account Holder", placeholder="Same as trainer name")
                account_number = st.text_input("Account Number")
            
            address = st.text_area("Address", placeholder="Full address")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                ifsc = st.text_input("IFSC Code", placeholder="SBIN0001234")
            with col2:
                account_type = st.selectbox("Account Type", ["Savings Account", "Current Account"])
            with col3:
                bank_name = st.text_input("Bank Name", placeholder="State Bank of India")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.form_submit_button("Add Trainer", type="primary"):
                    if not name or not rate:
                        st.error("Name and hourly rate are required")
                    else:
                        add_trainer({
                            'name': name, 'email': email, 'phone': phone,
                            'address': address, 'pan': pan.upper(), 'gstin': gstin.upper(),
                            'rate_per_hour': rate,
                            'account_holder': account_holder or name,
                            'account_number': account_number, 'ifsc': ifsc.upper(),
                            'account_type': account_type, 'bank_name': bank_name
                        })
                        st.success(f"✅ {name} added successfully!")
                        st.session_state.show_add_trainer = False
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_add_trainer = False
                    st.rerun()
    
    st.subheader(f"{len(trainers)} Trainer{'s' if len(trainers) != 1 else ''}")
    
    if len(trainers) > 0:
        for idx, row in trainers.iterrows():
            with st.expander(f"**{row['name']}** — ₹{row['rate_per_hour']:,.0f}/hr"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("**Contact:**")
                    st.write(f"📧 {row['email']}")
                    st.write(f"📱 {row['phone']}")
                    st.write(f"📍 {row['address']}")
                
                with col2:
                    st.write("**Tax Info:**")
                    st.write(f"PAN: {row['pan']}")
                    gstin_badge = "✅ Registered" if row['gstin'] != 'NA' else "⚠️ Unregistered"
                    st.write(f"GSTIN: {row['gstin']} {gstin_badge}")
                
                with col3:
                    st.write("**Bank Details:**")
                    st.write(f"Account: {row['account_number']}")
                    st.write(f"IFSC: {row['ifsc']}")
                    st.write(f"Bank: {row['bank_name']}")
                
                if st.button(f"🗑️ Delete {row['name']}", key=f"del_{row['id']}"):
                    delete_trainer(row['id'])
                    st.success(f"Deleted {row['name']}")
                    st.rerun()
    else:
        st.info("No trainers yet. Click 'Add Trainer' to get started!")

def show_sessions():
    st.title("📅 Sessions")
    
    trainers = get_trainers()
    if len(trainers) == 0:
        st.warning("⚠️ Please add trainers first before logging sessions.")
        return
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Log Session", type="primary", use_container_width=True):
            st.session_state.show_add_session = True
    
    if st.session_state.get('show_add_session', False):
        with st.form("add_session_form"):
            st.subheader("Log New Session")
            
            col1, col2 = st.columns(2)
            with col1:
                trainer_id = st.selectbox(
                    "Trainer *",
                    options=trainers['id'].tolist(),
                    format_func=lambda x: trainers[trainers['id']==x]['name'].iloc[0]
                )
                college = st.text_input("College Name *", placeholder="e.g. RV College of Engineering")
                program = st.text_input("Program/Subject", placeholder="e.g. Data Analytics")
                topic = st.text_input("Topic", placeholder="e.g. Introduction to Python")
            
            with col2:
                session_date = st.date_input("Session Date *", value=datetime.now())
                hours = st.number_input("Duration (hours) *", min_value=0.5, max_value=24.0, value=3.0, step=0.5)
                students = st.number_input("Number of Students", min_value=0, value=0, step=1)
                po_number = st.text_input("PO Number (optional)")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.form_submit_button("Log Session", type="primary"):
                    if not college or not hours:
                        st.error("College and hours are required")
                    else:
                        add_session({
                            'trainer_id': trainer_id,
                            'college': college,
                            'session_date': session_date.strftime("%Y-%m-%d"),
                            'hours': hours,
                            'students': students,
                            'topic': topic,
                            'program_name': program,
                            'po_number': po_number
                        })
                        st.success("✅ Session logged successfully!")
                        st.session_state.show_add_session = False
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_add_session = False
                    st.rerun()
    
    st.subheader("Filter Sessions")
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_trainer = st.selectbox(
            "Trainer",
            options=[None] + trainers['id'].tolist(),
            format_func=lambda x: "All Trainers" if x is None else trainers[trainers['id']==x]['name'].iloc[0]
        )
    with col2:
        filter_month = st.text_input("Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
    with col3:
        if st.button("Clear Filters"):
            st.session_state.filter_trainer = None
            st.session_state.filter_month = ""
            st.rerun()
    
    sessions = get_sessions(filter_trainer, filter_month if filter_month else None)
    
    st.subheader(f"{len(sessions)} Session{'s' if len(sessions) != 1 else ''}")
    
    if len(sessions) > 0:
        # Calculate fee column
        sessions['fee'] = sessions['hours'] * sessions['rate_per_hour']
        
        # Display table
        display_df = sessions[['session_date', 'trainer_name', 'college', 'topic', 'hours', 'students', 'fee']].copy()
        display_df.columns = ['Date', 'Trainer', 'College', 'Topic', 'Hours', 'Students', 'Fee (₹)']
        st.dataframe(display_df, use_container_width=True)
        
        # Delete sessions
        with st.expander("🗑️ Delete Sessions"):
            for idx, row in sessions.iterrows():
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.write(f"{row['session_date']} — {row['trainer_name']} — {row['college']}")
                with col2:
                    if st.button("Delete", key=f"delsess_{row['id']}"):
                        delete_session(row['id'])
                        st.success("Deleted")
                        st.rerun()
    else:
        st.info("No sessions found for the selected filters.")

def show_invoices():
    st.title("📄 Generate Invoice")
    
    trainers = get_trainers()
    if len(trainers) == 0:
        st.warning("⚠️ Please add trainers first.")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        trainer_id = st.selectbox(
            "Select Trainer *",
            options=trainers['id'].tolist(),
            format_func=lambda x: trainers[trainers['id']==x]['name'].iloc[0]
        )
    
    with col2:
        invoice_month_input = st.text_input("Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
    
    with col3:
        format_style = st.selectbox(
            "Invoice Style",
            options=["pavithra", "saiful"],
            format_func=lambda x: "Per-session breakdown" if x == "pavithra" else "Consolidated"
        )
    
    col1, col2 = st.columns(2)
    with col1:
        po_number = st.text_input("PO Number (optional)")
    with col2:
        tds_percent = st.number_input("TDS Deduction %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
    
    # Get sessions for selected trainer and month
    sessions = get_sessions(trainer_id, invoice_month_input)
    
    if len(sessions) == 0:
        st.warning(f"⚠️ No sessions found for this trainer in {invoice_month_input}")
        return
    
    st.subheader(f"Sessions for Invoice ({len(sessions)} sessions)")
    
    # Show sessions with checkboxes
    selected_sessions = []
    for idx, row in sessions.iterrows():
        col1, col2 = st.columns([1, 9])
        with col1:
            is_selected = st.checkbox("", value=True, key=f"sess_{row['id']}")
        with col2:
            fee = row['hours'] * row['rate_per_hour']
            st.write(f"**{row['session_date']}** — {row['college']} — {row['hours']}h — ₹{fee:,.0f}")
        
        if is_selected:
            selected_sessions.append(row)
    
    if len(selected_sessions) == 0:
        st.warning("Select at least one session to generate invoice")
        return
    
    # Calculate totals
    trainer = trainers[trainers['id'] == trainer_id].iloc[0]
    rate = trainer['rate_per_hour']
    
    if format_style == "saiful":
        total_qty = sum(s['hours'] for s in selected_sessions)
        subtotal = total_qty * rate
    else:
        subtotal = sum(s['hours'] * rate for s in selected_sessions)
    
    gst_amt = 0  # Assuming 0% GST as in samples
    total = subtotal + gst_amt
    tds_amt = round(total * tds_percent / 100)
    net_payable = total - tds_amt
    
    # Preview
    st.subheader("💰 Preview Totals")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Subtotal", f"₹{subtotal:,.0f}")
    col2.metric("GST", f"₹{gst_amt:,.0f}")
    col3.metric("Total", f"₹{total:,.0f}")
    col4.metric("Net Payable", f"₹{net_payable:,.0f}", delta=f"-₹{tds_amt:,.0f} TDS" if tds_amt > 0 else None)
    
    # Generate button
    if st.button("🎯 Generate PDF Invoice", type="primary", use_container_width=True):
        with st.spinner("Generating invoice..."):
            # Build invoice data
            invoice_number = get_next_invoice_number()
            
            # Format month display
            try:
                y, m = invoice_month_input.split('-')
                month_display = datetime(int(y), int(m), 1).strftime("%b %Y")
            except:
                month_display = invoice_month_input
            
            training_dates = format_dates([s['session_date'] for s in selected_sessions])
            invoice_date = f"{ordinal(datetime.now().day)} {datetime.now().strftime('%b')}"
            
            program_name = selected_sessions[0].get('program_name') or "Training Sessions"
            
            if format_style == "saiful":
                inv_sessions = [{
                    "description": f"{program_name} Offline Sessions",
                    "hsn_code": f"SES-{program_name[:8].upper()}",
                    "gst_label": "NA",
                    "gst_rate": 0,
                    "commercial": f"{int(rate):,}",
                    "quantity": total_qty,
                    "rate_per_unit": rate,
                }]
            else:
                inv_sessions = []
                for s in selected_sessions:
                    inv_sessions.append({
                        "description": f"{s['college']} - {s.get('topic') or program_name}",
                        "hsn_code": "NA",
                        "gst_rate": 0,
                        "quantity": s['hours'],
                        "rate_per_unit": rate,
                    })
            
            data = {
                "trainer_name": trainer['name'],
                "address": trainer['address'] or "",
                "gstin": trainer['gstin'] or "NA",
                "pan": trainer['pan'] or "",
                "email": trainer['email'] or "",
                "phone": trainer['phone'] or "",
                "account_holder": trainer['account_holder'] or trainer['name'],
                "account_number": trainer['account_number'] or "",
                "ifsc": trainer['ifsc'] or "",
                "account_type": trainer['account_type'] or "Savings Account",
                "bank_name": trainer['bank_name'] or "",
                "show_pan_in_bank": format_style == "saiful",
                "invoice_month": month_display,
                "invoice_date": invoice_date,
                "invoice_number": invoice_number,
                "po_number": po_number,
                "training_dates": training_dates,
                "program_name": program_name,
                "billed_to_name": BILLED_TO["name"],
                "billed_to_address": BILLED_TO["address"],
                "billed_to_gstin": BILLED_TO["gstin"],
                "tds_percent": tds_percent,
                "sessions": inv_sessions,
            }
            
            # Generate PDF in memory
            pdf_buffer = BytesIO()
            temp_path = f"/tmp/{invoice_number}.pdf"
            generate_invoice(data, temp_path)
            
            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()
            
            # Save invoice record
            save_invoice_record(invoice_number, trainer_id, month_display, total, net_payable)
            
            st.success(f"✅ Invoice {invoice_number} generated successfully!")
            
            # Download button
            st.download_button(
                label="📥 Download Invoice PDF",
                data=pdf_bytes,
                file_name=f"{trainer['name'].replace(' ', '_')}_{invoice_number}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

# ── Main App ──────────────────────────────────────────────────────────────────
def main():
    init_db()
    
    # Sidebar navigation
    st.sidebar.title("📄 Invoice Automation")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Trainers", "Sessions", "Generate Invoice"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Multi-user invoice automation system")
    st.sidebar.caption("Built with Streamlit 🎈")
    
    # Route to pages
    if page == "Dashboard":
        show_dashboard()
    elif page == "Trainers":
        show_trainers()
    elif page == "Sessions":
        show_sessions()
    elif page == "Generate Invoice":
        show_invoices()

if __name__ == "__main__":
    main()
