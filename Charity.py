import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import json
import os
import uuid
import io
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- PDF IMPORTS ---
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# --- CONSTANTS ---
DATA_FILE = "charity_data.csv"
MEMBERS_FILE = "members.json"
CURRENCY = "€"

INCOME_TYPES = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
OUTGOING_TYPES = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
MEDICAL_SUB_TYPES = ["Heart", "Cancer", "Lung", "Brain", "Bone", "Other"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
YEARS = [str(y) for y in range(2023, 2101)]

# --- QUOTES ---
QURAN_QUOTE = """ "The example of those who spend their wealth in the way of Allah is like a seed [of grain] which grows seven spikes, in each spike is a hundred grains. And Allah multiplies [His reward] for whom He wills. And Allah is all-Encompassing and Knowing." (Surah Al-Baqarah 2:261)"""
HADITH_QUOTE = """The Prophet (peace and blessings of Allah be upon him) said: "Protect yourselves from the Fire, even with half a date." (Sunan an-Nasa'i, 2552)"""

class CharityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Charity Management System - Desktop Edition")
        
        # Window State
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry("1400x900")
        
        # Initialize Data
        self.df = self.load_data()
        self.members_db = self.load_members()
        
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Layout
        self.create_dashboard_header()
        self.create_tabs()
        
        # Initial Refresh
        self.refresh_all_views()

    # --- DATA HANDLING ---
    def load_data(self):
        cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"]
        if os.path.exists(DATA_FILE):
            try:
                df = pd.read_csv(DATA_FILE)
                for c in cols:
                    if c not in df.columns: df[c] = ""
                return df
            except: pass
        return pd.DataFrame(columns=cols)

    def save_data(self):
        self.df.to_csv(DATA_FILE, index=False)
        self.refresh_dashboard()
        self.refresh_tables()

    def load_members(self):
        if os.path.exists(MEMBERS_FILE):
            try:
                with open(MEMBERS_FILE, 'r') as f: return json.load(f)
            except: pass
        return {}

    def save_members(self):
        with open(MEMBERS_FILE, 'w') as f: json.dump(self.members_db, f)
        self.refresh_all_views()

    def get_fund_balance(self, category):
        if self.df.empty: return 0.0
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0)
        inc = self.df[(self.df['Type'] == 'Incoming') & (self.df['Category'] == category)]['Amount'].sum()
        out = self.df[(self.df['Type'] == 'Outgoing') & (self.df['Category'] == category)]['Amount'].sum()
        return inc - out

    def refresh_all_views(self):
        """Master refresh function"""
        self.refresh_dashboard()
        self.update_member_dropdown() # Updates Tab 1 dropdown
        self.refresh_member_list_tab() # Updates Tab 6 list
        self.refresh_tables() # Updates Tab 2, 3 tables

    # --- UI LAYOUT ---
    def create_dashboard_header(self):
        frame = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief=tk.RAISED)
        frame.pack(side=tk.TOP, fill=tk.X)
        
        self.lbl_stats = tk.Label(frame, text="Loading...", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#333")
        self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.lbl_funds = tk.Label(frame, text="", font=("Consolas", 10), bg="#f0f0f0", fg="#006400")
        self.lbl_funds.pack(side=tk.RIGHT, padx=20, pady=10)

    def refresh_dashboard(self):
        if self.df.empty: 
            self.lbl_stats.config(text="No Data Available")
            return
        
        # Calculate Stats
        curr_yr = datetime.now().year
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0)
        
        tot_inc = self.df[self.df['Type'] == 'Incoming']['Amount'].sum()
        yr_inc = self.df[(self.df['Type'] == 'Incoming') & (self.df['Year'] == curr_yr)]['Amount'].sum()
        tot_don = self.df[self.df['Type'] == 'Outgoing']['Amount'].sum()
        yr_don = self.df[(self.df['Type'] == 'Outgoing') & (self.df['Year'] == curr_yr)]['Amount'].sum()
        
        stats_text = (f"TOTAL INCOME: {CURRENCY}{tot_inc:,.2f}  |  INCOME ({curr_yr}): {CURRENCY}{yr_inc:,.2f}\n"
                      f"TOTAL DONATION: {CURRENCY}{tot_don:,.2f} |  DONATION ({curr_yr}): {CURRENCY}{yr_don:,.2f}")
        self.lbl_stats.config(text=stats_text, fg="darkblue")
        
        # Funds
        fund_txt = "BALANCES: "
        for cat in INCOME_TYPES:
            bal = self.get_fund_balance(cat)
            fund_txt += f"{cat}: {CURRENCY}{bal:,.2f} | "
        self.lbl_funds.config(text=fund_txt)

    def create_tabs(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)
        
        # FIX: Naming these correctly so setup functions can find them
        self.tab_trans = ttk.Frame(nb)
        self.tab_log = ttk.Frame(nb)
        self.tab_don = ttk.Frame(nb)
        self.tab_ana = ttk.Frame(nb)
        self.tab_rep = ttk.Frame(nb)
        self.tab_mem = ttk.Frame(nb)
        
        nb.add(self.tab_mem, text="1. Member Management")
        nb.add(self.tab_trans, text="2. Transaction Entry")
        nb.add(self.tab_log, text="3. Activity Log")
        nb.add(self.tab_don, text="4. Donation List")
        nb.add(self.tab_ana, text="5. Analysis")
        nb.add(self.tab_rep, text="6. Member Reports")
        
        
        self.setup_member_tab()
        self.setup_transaction_tab()
        self.setup_log_tab()
        self.setup_donation_tab()
        self.setup_analysis_tab()
        self.setup_report_tab()
        

    # --- TAB 1: TRANSACTION ---
    def setup_transaction_tab(self):
        main = ttk.Frame(self.tab_trans)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Type Selection
        type_frame = ttk.LabelFrame(main, text="Transaction Type")
        type_frame.pack(fill="x", pady=5)
        
        self.var_type = tk.StringVar(value="Incoming")
        ttk.Radiobutton(type_frame, text="INCOMING (Collection)", variable=self.var_type, value="Incoming", command=self.update_form_view).pack(side="left", padx=20, pady=10)
        ttk.Radiobutton(type_frame, text="OUTGOING (Donation)", variable=self.var_type, value="Outgoing", command=self.update_form_view).pack(side="left", padx=20, pady=10)
        
        # 2. Date & Amount
        common_frame = ttk.LabelFrame(main, text="Details")
        common_frame.pack(fill="x", pady=5)
        
        f1 = tk.Frame(common_frame); f1.pack(fill="x", padx=10, pady=5)
        tk.Label(f1, text="Year:").pack(side="left")
        self.ent_year = ttk.Combobox(f1, values=YEARS, width=5); self.ent_year.set(datetime.now().year); self.ent_year.pack(side="left", padx=5)
        
        tk.Label(f1, text="Month:").pack(side="left")
        self.ent_month = ttk.Combobox(f1, values=MONTH_NAMES, width=10); self.ent_month.set(MONTH_NAMES[datetime.now().month-1]); self.ent_month.pack(side="left", padx=5)
        
        tk.Label(f1, text="Day:").pack(side="left")
        self.ent_day = ttk.Spinbox(f1, from_=1, to=31, width=3); self.ent_day.set(datetime.now().day); self.ent_day.pack(side="left", padx=5)
        
        tk.Label(f1, text=f"Amount ({CURRENCY}):", font=("Arial", 10, "bold")).pack(side="left", padx=20)
        self.ent_amt = ttk.Entry(f1, width=15); self.ent_amt.pack(side="left")

        # 3. Dynamic Inputs
        self.f_incoming = tk.Frame(common_frame)
        self.f_outgoing = tk.Frame(common_frame)
        
        # INCOMING FIELDS
        tk.Label(self.f_incoming, text="Group:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.var_inc_grp = tk.StringVar(value="Brother")
        tk.Radiobutton(self.f_incoming, text="Brother", variable=self.var_inc_grp, value="Brother", command=self.update_member_dropdown).grid(row=0, column=1)
        tk.Radiobutton(self.f_incoming, text="Sister", variable=self.var_inc_grp, value="Sister", command=self.update_member_dropdown).grid(row=0, column=2)
        
        tk.Label(self.f_incoming, text="Member Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ent_inc_name = ttk.Combobox(self.f_incoming, width=30)
        self.ent_inc_name.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        tk.Label(self.f_incoming, text="Category:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.ent_inc_cat = ttk.Combobox(self.f_incoming, values=INCOME_TYPES, width=30); self.ent_inc_cat.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        # OUTGOING FIELDS
        tk.Label(self.f_outgoing, text="Beneficiary Name:").grid(row=0, column=0, sticky="w"); self.out_ben = ttk.Entry(self.f_outgoing, width=25); self.out_ben.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(self.f_outgoing, text="Address:").grid(row=0, column=2, sticky="w"); self.out_addr = ttk.Entry(self.f_outgoing, width=25); self.out_addr.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(self.f_outgoing, text="Responsible Person:").grid(row=1, column=0, sticky="w"); self.out_resp = ttk.Combobox(self.f_outgoing, width=22); self.out_resp.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(self.f_outgoing, text="Reason/Note:").grid(row=1, column=2, sticky="w"); self.out_reason = ttk.Entry(self.f_outgoing, width=25); self.out_reason.grid(row=1, column=3, padx=5, pady=2)

        tk.Label(self.f_outgoing, text="Group:").grid(row=2, column=0, sticky="w"); self.out_grp = ttk.Combobox(self.f_outgoing, values=["Brother", "Sister"], width=22); self.out_grp.grid(row=2, column=1, padx=5, pady=2)
        tk.Label(self.f_outgoing, text="Fund Source:").grid(row=2, column=2, sticky="w"); self.out_fund = ttk.Combobox(self.f_outgoing, values=INCOME_TYPES, width=22); self.out_fund.grid(row=2, column=3, padx=5, pady=2)
        
        tk.Label(self.f_outgoing, text="Usage Type:").grid(row=3, column=0, sticky="w"); self.out_use = ttk.Combobox(self.f_outgoing, values=OUTGOING_TYPES, width=22); self.out_use.grid(row=3, column=1, padx=5, pady=2)
        self.out_use.bind("<<ComboboxSelected>>", self.check_medical)
        
        self.lbl_med = tk.Label(self.f_outgoing, text="Condition:"); self.ent_med = ttk.Combobox(self.f_outgoing, values=MEDICAL_SUB_TYPES, width=22)

        ttk.Button(main, text="💾 SAVE TRANSACTION", command=self.submit_transaction).pack(pady=20)
        
        # Last 5
        last5_frame = ttk.LabelFrame(main, text="Last 5 Entries")
        last5_frame.pack(fill="both", expand=True)
        cols = ("Date", "Type", "Name", "Category", "Amount")
        self.tree_last5 = ttk.Treeview(last5_frame, columns=cols, show="headings", height=5)
        for c in cols: self.tree_last5.heading(c, text=c)
        self.tree_last5.pack(fill="both", expand=True)
        
        self.update_form_view()

    def update_form_view(self):
        if self.var_type.get() == "Incoming":
            self.f_outgoing.pack_forget()
            self.f_incoming.pack(fill="x", padx=10, pady=5)
        else:
            self.f_incoming.pack_forget()
            self.f_outgoing.pack(fill="x", padx=10, pady=5)
            # Update responsible list
            all_mems = sorted(list(self.members_db.keys()))
            self.out_resp['values'] = all_mems

    def check_medical(self, event=None):
        if self.out_use.get() == "Medical help":
            self.lbl_med.grid(row=3, column=2, sticky="w", padx=5)
            self.ent_med.grid(row=3, column=3, padx=5)
        else:
            self.lbl_med.grid_remove()
            self.ent_med.grid_remove()
            self.ent_med.set("")

    def update_member_dropdown(self):
        # Explicitly checks the current group selection variable and filters the list
        grp = self.var_inc_grp.get()
        # Find members where 'group' matches selection
        mems = [name for name, data in self.members_db.items() if data.get('group') == grp]
        self.ent_inc_name['values'] = sorted(mems)
        # Clear current selection if not in new list
        if self.ent_inc_name.get() not in mems:
            self.ent_inc_name.set('')

    def submit_transaction(self):
        try:
            amt = float(self.ent_amt.get())
            if amt <= 0: raise ValueError
            
            y, d = int(self.ent_year.get()), int(self.ent_day.get())
            m = MONTH_NAMES.index(self.ent_month.get()) + 1
            date_str = f"{y}-{m:02d}-{d:02d}"
            
            row = {
                "ID": str(uuid.uuid4()), "Date": date_str, "Year": y, "Month": m,
                "Type": self.var_type.get(), "Amount": amt,
                "Name_Details": "", "Group": "", "Category": "", "SubCategory": "", "Medical": "", 
                "Address": "", "Reason": "", "Responsible": ""
            }
            
            if row['Type'] == "Incoming":
                if not self.ent_inc_name.get(): return messagebox.showerror("Error", "Name required")
                row.update({
                    "Name_Details": self.ent_inc_name.get(),
                    "Group": self.var_inc_grp.get(),
                    "Category": self.ent_inc_cat.get()
                })
            else:
                fund = self.out_fund.get()
                bal = self.get_fund_balance(fund)
                if amt > bal: return messagebox.showerror("Error", f"Insufficient funds in {fund}")
                
                row.update({
                    "Name_Details": self.out_ben.get(),
                    "Address": self.out_addr.get(),
                    "Reason": self.out_reason.get(),
                    "Responsible": self.out_resp.get(),
                    "Group": self.out_grp.get(),
                    "Category": fund,
                    "SubCategory": self.out_use.get(),
                    "Medical": self.ent_med.get()
                })
                
            self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
            self.save_data()
            messagebox.showinfo("Success", "Transaction Saved")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid Amount")

    # --- TAB 6: MEMBER MANAGEMENT (EXPANDED) ---
    def setup_member_tab(self):
        # Split Frame: Left (Form), Right (Table)
        paned = tk.PanedWindow(self.tab_mem, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        left_f = tk.LabelFrame(paned, text="Register / Edit Member", padx=10, pady=10)
        right_f = tk.LabelFrame(paned, text="Registered Members List", padx=10, pady=10)
        
        paned.add(left_f, width=400)
        paned.add(right_f)
        
        # FORM
        tk.Label(left_f, text="Full Name:").pack(anchor="w")
        self.mem_name = ttk.Entry(left_f); self.mem_name.pack(fill="x", pady=2)
        
        tk.Label(left_f, text="Member ID (Optional):").pack(anchor="w")
        self.mem_id = ttk.Entry(left_f); self.mem_id.pack(fill="x", pady=2)
        
        tk.Label(left_f, text="Group:").pack(anchor="w", pady=(10, 0))
        self.mem_grp = tk.StringVar(value="Brother")
        ttk.Radiobutton(left_f, text="Brother", variable=self.mem_grp, value="Brother").pack(anchor="w")
        ttk.Radiobutton(left_f, text="Sister", variable=self.mem_grp, value="Sister").pack(anchor="w")
        
        tk.Label(left_f, text="Phone:").pack(anchor="w", pady=(10,0))
        self.mem_phone = ttk.Entry(left_f); self.mem_phone.pack(fill="x", pady=2)
        
        tk.Label(left_f, text="Email:").pack(anchor="w")
        self.mem_email = ttk.Entry(left_f); self.mem_email.pack(fill="x", pady=2)
        
        tk.Label(left_f, text="Address:").pack(anchor="w")
        self.mem_addr = ttk.Entry(left_f); self.mem_addr.pack(fill="x", pady=2)
        
        btn_f = tk.Frame(left_f)
        btn_f.pack(pady=20, fill="x")
        ttk.Button(btn_f, text="Save Member", command=self.save_member).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_member).pack(side="right", fill="x", expand=True, padx=2)

        # TABLE
        cols = ("Name", "ID", "Group", "Phone", "Email")
        self.tree_mems = ttk.Treeview(right_f, columns=cols, show="headings")
        for c in cols: self.tree_mems.heading(c, text=c)
        self.tree_mems.column("Name", width=150)
        self.tree_mems.column("ID", width=80)
        self.tree_mems.column("Group", width=80)
        
        vsb = ttk.Scrollbar(right_f, orient="vertical", command=self.tree_mems.yview)
        self.tree_mems.configure(yscrollcommand=vsb.set)
        
        self.tree_mems.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        self.refresh_member_list_tab()

    def save_member(self):
        name = self.mem_name.get().strip()
        if not name: return messagebox.showerror("Error", "Name required")
        
        mid = self.mem_id.get().strip()
        if not mid: mid = str(uuid.uuid4())[:8]
        
        self.members_db[name] = {
            "id": mid,
            "group": self.mem_grp.get(),
            "phone": self.mem_phone.get(),
            "email": self.mem_email.get(),
            "address": self.mem_addr.get(),
            "joined": datetime.now().strftime("%Y-%m-%d")
        }
        self.save_members()
        self.refresh_member_list_tab()
        
        # Clear form
        self.mem_name.delete(0, tk.END); self.mem_id.delete(0, tk.END)
        self.mem_phone.delete(0, tk.END); self.mem_email.delete(0, tk.END); self.mem_addr.delete(0, tk.END)
        messagebox.showinfo("Success", "Member Saved")

    def delete_member(self):
        sel = self.tree_mems.selection()
        if not sel: return
        name = self.tree_mems.item(sel[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Delete {name}?"):
            del self.members_db[name]
            self.save_members()
            self.refresh_member_list_tab()

    def refresh_member_list_tab(self):
        for i in self.tree_mems.get_children(): self.tree_mems.delete(i)
        for name, data in self.members_db.items():
            self.tree_mems.insert("", "end", values=(name, data.get("id"), data.get("group"), data.get("phone"), data.get("email")))

    # --- TAB 2: LOG ---
    def setup_log_tab(self):
        # Filters
        f = tk.Frame(self.tab_log); f.pack(fill="x", padx=10, pady=5)
        self.log_yr = ttk.Combobox(f, values=["All"] + YEARS, width=6); self.log_yr.set("All"); self.log_yr.pack(side="left")
        self.log_type = ttk.Combobox(f, values=["All", "Incoming", "Outgoing"], width=10); self.log_type.set("All"); self.log_type.pack(side="left", padx=5)
        ttk.Button(f, text="Refresh", command=self.refresh_tables).pack(side="left")
        ttk.Button(f, text="Delete Selected", command=self.delete_transaction).pack(side="right")
        
        cols = ("Date", "Type", "Name", "Category", "Sub/Med", "Amount", "ID")
        self.tree_log = ttk.Treeview(self.tab_log, columns=cols, show="headings")
        for c in cols: 
            self.tree_log.heading(c, text=c)
            if c == "ID": self.tree_log.column(c, width=0, stretch=False)
            else: self.tree_log.column(c, width=100)
        self.tree_log.pack(fill="both", expand=True, padx=10)

    def delete_transaction(self):
        sel = self.tree_log.selection()
        if not sel: return
        if messagebox.askyesno("Confirm", "Delete selected transaction?"):
            ids = [self.tree_log.item(i)['values'][-1] for i in sel]
            self.df = self.df[~self.df['ID'].isin(ids)]
            self.save_data()

    def refresh_log(self):
        for i in self.tree_log.get_children(): self.tree_log.delete(i)
        yr = self.log_yr.get()
        v = self.df.copy()
        if yr != "All": v = v[v['Year'] == int(yr)]
        
        for _, r in v.iterrows():
            sub = r['SubCategory'] if r['Type'] == 'Outgoing' else ""
            if r['Medical']: sub += f" ({r['Medical']})"
            self.tree_log.insert("", "end", values=(r['Date'], r['Type'], r['Name_Details'], r['Category'], sub, f"{r['Amount']:.2f}", r['ID']))

    # --- TAB 3: DONATION LIST ---
    def setup_donation_tab(self):
        f = tk.Frame(self.tab_don); f.pack(fill="x", padx=10, pady=5)
        self.don_yr = ttk.Combobox(f, values=["All"] + YEARS); self.don_yr.set("All"); self.don_yr.pack(side="left")
        self.don_grp = ttk.Combobox(f, values=["All", "Brother", "Sister"]); self.don_grp.set("All"); self.don_grp.pack(side="left", padx=5)
        ttk.Button(f, text="Refresh", command=self.refresh_tables).pack(side="left")
        
        cols = ("Date", "Beneficiary", "Category", "Sub", "Amount")
        self.tree_don = ttk.Treeview(self.tab_don, columns=cols, show="headings")
        for c in cols: self.tree_don.heading(c, text=c)
        self.tree_don.pack(fill="both", expand=True, padx=10)

    def refresh_donations(self):
        for i in self.tree_don.get_children(): self.tree_don.delete(i)
        don_df = self.df[self.df['Type'] == 'Outgoing']
        for _, r in don_df.iterrows():
            self.tree_don.insert("", "end", values=(r['Date'], r['Name_Details'], r['Category'], r['SubCategory'], f"{r['Amount']:.2f}"))

    # --- TAB 4: ANALYSIS ---
    def setup_analysis_tab(self):
        # Using Matplotlib inside Tkinter
        f = tk.Frame(self.tab_ana); f.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=f)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        ttk.Button(self.tab_ana, text="Update Charts", command=self.plot_analysis).pack()

    def plot_analysis(self):
        self.ax1.clear(); self.ax2.clear()
        
        inc = self.df[self.df['Type'] == "Incoming"]
        if not inc.empty:
            ig = inc.groupby("Category")['Amount'].sum()
            self.ax1.pie(ig, labels=ig.index, autopct='%1.1f%%')
            self.ax1.set_title("Income Sources")
            
        out = self.df[self.df['Type'] == "Outgoing"]
        if not out.empty:
            og = out.groupby("Category")['Amount'].sum()
            self.ax2.pie(og, labels=og.index, autopct='%1.1f%%')
            self.ax2.set_title("Donation Distribution")
            
        self.canvas.draw()

    # --- TAB 5: REPORTS & PDF ---
    def setup_report_tab(self):
        f = tk.Frame(self.tab_rep); f.pack(fill="x", padx=10, pady=10)
        tk.Label(f, text="Member:").pack(side="left")
        self.rep_mem = ttk.Combobox(f, width=20); self.rep_mem.pack(side="left", padx=5)
        self.rep_mem.bind("<Button-1>", lambda e: self.update_rep_dropdown())
        
        tk.Label(f, text="Year:").pack(side="left")
        self.rep_yr = ttk.Combobox(f, values=YEARS, width=6); self.rep_yr.set(str(datetime.now().year)); self.rep_yr.pack(side="left")
        
        ttk.Button(f, text="Generate PDF", command=self.generate_report_pdf).pack(side="left", padx=20)
        
        # Text Areas for Messages
        msg_frame = tk.LabelFrame(self.tab_rep, text="PDF Messages")
        msg_frame.pack(fill="x", padx=10)
        self.txt_header = tk.Text(msg_frame, height=2); self.txt_header.pack(fill="x", pady=2)
        self.txt_header.insert("1.0", "We appreciate your generous contributions.")
        
        self.txt_footer = tk.Text(msg_frame, height=2); self.txt_footer.pack(fill="x", pady=2)
        self.txt_footer.insert("1.0", "Contact admin for queries.")

    def update_rep_dropdown(self):
        mems = sorted(list(self.members_db.keys()))
        self.rep_mem['values'] = mems

    def generate_report_pdf(self):
        if not HAS_PDF: return messagebox.showerror("Error", "ReportLab not installed")
        name = self.rep_mem.get()
        if not name: return
        
        year = int(self.rep_yr.get())
        mdf = self.df[(self.df['Name_Details'] == name) & (self.df['Type'] == 'Incoming') & (self.df['Year'] == year)]
        
        # Prepare Data
        mem_info = self.members_db.get(name, {})
        fname = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{name}_{year}.pdf")
        if not fname: return
        
        try:
            doc = SimpleDocTemplate(fname, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Styles
            title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=20, textColor=colors.darkgreen)
            header_style = ParagraphStyle('Header', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12)
            quote_style = ParagraphStyle('Quote', parent=styles['Italic'], textColor=colors.darkblue)
            
            # Header
            elements.append(Paragraph("Bismillah hir Rahmanir Rahim", header_style))
            elements.append(Paragraph("Sadaka Group Berlin", title_style))
            elements.append(Paragraph("Member Contribution Report", styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            # Quotes
            elements.append(Paragraph(QURAN_QUOTE, quote_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(HADITH_QUOTE, quote_style))
            elements.append(Spacer(1, 20))
            
            # Member Info
            elements.append(Paragraph(f"<b>Member:</b> {name}", styles['Normal']))
            elements.append(Paragraph(f"<b>Details:</b> {mem_info.get('address','-')} | {mem_info.get('phone','-')}", styles['Normal']))
            elements.append(Spacer(1, 15))
            
            # Custom Header Msg
            elements.append(Paragraph(self.txt_header.get("1.0", "end-1c"), styles['Italic']))
            elements.append(Spacer(1, 15))
            
            # Table 1: Contributions
            elements.append(Paragraph(f"Contributions in {year}", styles['Heading3']))
            data1 = [["Date", "Category", "Amount"]]
            total = 0
            for _, r in mdf.iterrows():
                mname = MONTH_NAMES[r['Month']-1]
                data1.append([mname, r['Category'], f"{r['Amount']:.2f}"])
                total += r['Amount']
            data1.append(["", "TOTAL:", f"{total:.2f}"])
            
            t1 = Table(data1, colWidths=[100, 150, 100])
            t1.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkgreen),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t1); elements.append(Spacer(1, 20))
            
            # Table 2: Donations Distributed
            grp = mem_info.get('group', 'Brother')
            don_df = self.df[(self.df['Type'] == 'Outgoing') & (self.df['Year'] == year) & (self.df['Group'] == grp)]
            
            elements.append(Paragraph(f"Donations Distributed ({grp}s)", styles['Heading3']))
            data2 = [["Date", "Beneficiary", "Reason", "Amount"]]
            d_total = 0
            for _, r in don_df.iterrows():
                data2.append([r['Date'], r['Name_Details'], r['Reason'], f"{r['Amount']:.2f}"])
                d_total += r['Amount']
            data2.append(["", "", "TOTAL:", f"{d_total:.2f}"])
            
            t2 = Table(data2, colWidths=[80, 120, 150, 80])
            t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black), ('FONTSIZE', (0,0), (-1,-1), 8)]))
            elements.append(t2)
            
            # Footer
            elements.append(Spacer(1, 30))
            elements.append(Paragraph(self.txt_footer.get("1.0", "end-1c"), styles['Normal']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("_______________________", styles['Normal']))
            elements.append(Paragraph("Authorized Signature", styles['Normal']))
            
            doc.build(elements)
            messagebox.showinfo("Success", f"PDF Saved: {fname}")
            
        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    def refresh_tables(self):
        # Refresh Last 5
        for i in self.tree_last5.get_children(): self.tree_last5.delete(i)
        rec = self.df.tail(5)
        for _, r in rec.iloc[::-1].iterrows():
            self.tree_last5.insert("", "end", values=(r['Date'], r['Type'], r['Name_Details'], r['Category'], f"{r['Amount']:.2f}"))
            
        self.refresh_log()
        self.refresh_donations()

if __name__ == "__main__":
    root = tk.Tk()
    app = CharityApp(root)
    root.mainloop()
