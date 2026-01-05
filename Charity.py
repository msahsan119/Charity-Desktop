import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
import json
import os
import uuid
import io
from datetime import datetime

# --- MATPLOTLIB SETUP (HEADLESS MODE FOR PDF) ---
import matplotlib
matplotlib.use('Agg') # Prevents popup windows during PDF generation
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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
SETTINGS_FILE = "settings.json"
CURRENCY = "€"

# Defaults
DEFAULT_INCOME = ["Sadaka", "Zakat", "Fitra", "Iftar", "Scholarship", "General"]
DEFAULT_OUTGOING = ["Medical help", "Financial help", "Karje hasana", "Mosque", "Dead body", "Scholarship"]
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
        self.root.title("Charity Management System - Professional Edition")
        
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry("1400x900")
        
        # State Variables
        self.editing_member_original_name = None

        # Load Data & Settings
        self.load_settings()
        self.df = self.load_data()
        self.members_db = self.load_members()
        
        # UI Setup
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        
        self.create_dashboard_header()
        self.create_tabs()
        
        # Initial Refresh
        self.refresh_all_views()

    # =========================================================================
    # DATA & SETTINGS HANDLING
    # =========================================================================
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.income_cats = data.get("income", DEFAULT_INCOME)
                    self.outgoing_cats = data.get("outgoing", DEFAULT_OUTGOING)
            except:
                self.income_cats = DEFAULT_INCOME
                self.outgoing_cats = DEFAULT_OUTGOING
        else:
            self.income_cats = DEFAULT_INCOME
            self.outgoing_cats = DEFAULT_OUTGOING

    def save_settings(self):
        data = {"income": self.income_cats, "outgoing": self.outgoing_cats}
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
        self.refresh_all_views()

    def load_data(self):
        cols = ["ID", "Date", "Year", "Month", "Type", "Group", "Name_Details", 
                "Address", "Reason", "Responsible", "Category", "SubCategory", "Medical", "Amount"]
        if os.path.exists(DATA_FILE):
            try:
                df = pd.read_csv(DATA_FILE)
                for c in cols:
                    if c not in df.columns: df[c] = ""
                df = df.fillna("")
                return df
            except: pass
        return pd.DataFrame(columns=cols)

    def save_data(self):
        self.df.to_csv(DATA_FILE, index=False)
        self.refresh_all_views()

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
        """Updates entire UI"""
        if hasattr(self, 'ent_inc_cat_manage'): self.ent_inc_cat_manage['values'] = self.income_cats
        if hasattr(self, 'out_fund'): self.out_fund['values'] = self.income_cats
        if hasattr(self, 'ent_out_cat_manage'): self.ent_out_cat_manage['values'] = self.outgoing_cats

        self.refresh_dashboard()
        self.update_member_dropdown()
        if hasattr(self, 'tree_mems'): self.refresh_member_list_tab()
        if hasattr(self, 'tree_log'): self.refresh_tables() 
        if hasattr(self, 'canvas'): self.plot_analysis()
        if hasattr(self, 'tree_matrix'): self.generate_matrix_report()
        
        mems = sorted(list(self.members_db.keys()))
        if hasattr(self, 'rep_mem'): self.rep_mem['values'] = mems
        if hasattr(self, 'matrix_cat'): 
            self.matrix_cat['values'] = ["All"] + self.income_cats
        if hasattr(self, 'tree_ana_cats'):
            self.update_analysis_tables()
        if hasattr(self, 'tree_ana_cats'):
            # Re-configure Category columns in case they changed
            new_cols = ["Month"] + self.income_cats + ["Total"]
            self.tree_ana_cats["columns"] = new_cols
            for c in new_cols:
                self.tree_ana_cats.heading(c, text=c)
                self.tree_ana_cats.column(c, width=60, anchor="center")
            self.tree_ana_cats.column("Month", width=80, anchor="w")
        
        self.refresh_analysis_views()

    # =========================================================================
    # UI COMPONENTS
    # =========================================================================
    def create_dashboard_header(self):
        frame = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief=tk.RAISED)
        frame.pack(side=tk.TOP, fill=tk.X)
        self.lbl_stats = tk.Label(frame, text="Loading...", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#333")
        self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=10)
        tk.Button(frame, text="⚙️ Manage Categories", command=self.open_category_manager, bg="#e1e1e1").pack(side=tk.RIGHT, padx=10, pady=5)
        self.lbl_funds = tk.Label(frame, text="", font=("Consolas", 10), bg="#f0f0f0", fg="#006400")
        self.lbl_funds.pack(side=tk.RIGHT, padx=20, pady=10)

    def open_category_manager(self):
        top = tk.Toplevel(self.root)
        top.title("Manage Categories")
        top.geometry("600x450")
        nb = ttk.Notebook(top); nb.pack(fill="both", expand=True, padx=10, pady=10)
        f_inc = tk.Frame(nb); nb.add(f_inc, text="Incoming Categories")
        f_out = tk.Frame(nb); nb.add(f_out, text="Usage/Outgoing Types")
        
        def build_ui(frame, current_list, list_type, db_col_name):
            lb = tk.Listbox(frame); lb.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            for item in current_list: lb.insert(tk.END, item)
            btn_f = tk.Frame(frame); btn_f.pack(side="right", fill="y")
            
            def add_item():
                new_cat = simpledialog.askstring("New", f"Enter new {list_type} category:")
                if new_cat and new_cat not in current_list:
                    current_list.append(new_cat); self.save_settings(); lb.insert(tk.END, new_cat)
            
            def edit_item():
                sel = lb.curselection()
                if sel:
                    old_val = lb.get(sel[0]); new_val = simpledialog.askstring("Edit", f"Rename '{old_val}' to:")
                    if new_val and new_val != old_val:
                        current_list[sel[0]] = new_val; self.save_settings()
                        lb.delete(sel[0]); lb.insert(sel[0], new_val)
                        if not self.df.empty:
                            self.df.loc[self.df[db_col_name] == old_val, db_col_name] = new_val
                            self.save_data(); messagebox.showinfo("Updated", f"Updated past transactions.")

            def del_item():
                sel = lb.curselection()
                if sel:
                    if messagebox.askyesno("Delete", f"Remove '{lb.get(sel[0])}'?"):
                        current_list.remove(lb.get(sel[0])); self.save_settings(); lb.delete(sel[0])

            tk.Button(btn_f, text="Add New", command=add_item).pack(fill="x", pady=5)
            tk.Button(btn_f, text="Edit & Update DB", command=edit_item).pack(fill="x", pady=5)
            tk.Button(btn_f, text="Delete", command=del_item).pack(fill="x", pady=5)

        build_ui(f_inc, self.income_cats, "Incoming", "Category")
        build_ui(f_out, self.outgoing_cats, "Outgoing", "SubCategory")

    def refresh_dashboard(self):
        if self.df.empty: 
            self.lbl_stats.config(text="No Data Available")
            return
        curr_yr = datetime.now().year
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0)
        
        tot_inc = self.df[self.df['Type'] == 'Incoming']['Amount'].sum()
        yr_inc = self.df[(self.df['Type'] == 'Incoming') & (self.df['Year'] == curr_yr)]['Amount'].sum()
        tot_don = self.df[self.df['Type'] == 'Outgoing']['Amount'].sum()
        yr_don = self.df[(self.df['Type'] == 'Outgoing') & (self.df['Year'] == curr_yr)]['Amount'].sum()
        
        stats_text = (f"TOTAL INCOME: {CURRENCY}{tot_inc:,.2f}  |  INCOME ({curr_yr}): {CURRENCY}{yr_inc:,.2f}\n"
                      f"TOTAL DONATION: {CURRENCY}{tot_don:,.2f} |  DONATION ({curr_yr}): {CURRENCY}{yr_don:,.2f}")
        self.lbl_stats.config(text=stats_text, fg="darkblue")
        
        fund_txt = "BALANCES: "
        for cat in self.income_cats:
            bal = self.get_fund_balance(cat)
            fund_txt += f"{cat}: {CURRENCY}{bal:,.2f} | "
        self.lbl_funds.config(text=fund_txt)

    def create_tabs(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_mem = ttk.Frame(nb); nb.add(self.tab_mem, text="1. Member Management")
        self.tab_trans = ttk.Frame(nb); nb.add(self.tab_trans, text="2. Transaction")
        self.tab_log = ttk.Frame(nb); nb.add(self.tab_log, text="3. Activity Log")
        self.tab_don = ttk.Frame(nb); nb.add(self.tab_don, text="4. Donation List")
        self.tab_matrix = ttk.Frame(nb); nb.add(self.tab_matrix, text="5. Overall Matrix")
        self.tab_ana = ttk.Frame(nb); nb.add(self.tab_ana, text="6. Analysis")
        self.tab_rep = ttk.Frame(nb); nb.add(self.tab_rep, text="7. Member Reports")
        
        
        self.setup_transaction_tab()
        self.setup_log_tab()
        self.setup_donation_tab()
        self.setup_analysis_tab()
        self.setup_report_tab()
        self.setup_member_tab()
        self.setup_overall_contribution_tab()

    # --- TAB 2: TRANSACTION ---
    def setup_transaction_tab(self):
        main = ttk.Frame(self.tab_trans)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        type_frame = ttk.LabelFrame(main, text="Transaction Type")
        type_frame.pack(fill="x", pady=5)
        self.var_type = tk.StringVar(value="Incoming")
        ttk.Radiobutton(type_frame, text="INCOMING (Collection)", variable=self.var_type, value="Incoming", command=self.update_form_view).pack(side="left", padx=20, pady=10)
        ttk.Radiobutton(type_frame, text="OUTGOING (Donation)", variable=self.var_type, value="Outgoing", command=self.update_form_view).pack(side="left", padx=20, pady=10)
        
        common_frame = ttk.LabelFrame(main, text="Details")
        common_frame.pack(fill="x", pady=5)
        f1 = tk.Frame(common_frame); f1.pack(fill="x", padx=10, pady=5)
        
        tk.Label(f1, text="Date (D/M/Y):").pack(side="left")
        self.ent_day = ttk.Spinbox(f1, from_=1, to=31, width=3); self.ent_day.set(datetime.now().day); self.ent_day.pack(side="left")
        self.ent_month = ttk.Combobox(f1, values=MONTH_NAMES, width=10); self.ent_month.set(MONTH_NAMES[datetime.now().month-1]); self.ent_month.pack(side="left")
        self.ent_year = ttk.Combobox(f1, values=YEARS, width=5); self.ent_year.set(datetime.now().year); self.ent_year.pack(side="left")
        
        tk.Label(f1, text=f"Amount ({CURRENCY}):", font=("Arial", 10, "bold")).pack(side="left", padx=20)
        self.ent_amt = ttk.Entry(f1, width=15); self.ent_amt.pack(side="left")

        self.f_incoming = tk.Frame(common_frame)
        self.f_outgoing = tk.Frame(common_frame)
        
        # INCOMING
        tk.Label(self.f_incoming, text="Group:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.var_inc_grp = tk.StringVar(value="Brother")
        tk.Radiobutton(self.f_incoming, text="Brother", variable=self.var_inc_grp, value="Brother", command=self.update_member_dropdown).grid(row=0, column=1)
        tk.Radiobutton(self.f_incoming, text="Sister", variable=self.var_inc_grp, value="Sister", command=self.update_member_dropdown).grid(row=0, column=2)
        tk.Label(self.f_incoming, text="Member Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ent_inc_name = ttk.Combobox(self.f_incoming, width=30)
        self.ent_inc_name.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        tk.Label(self.f_incoming, text="Category:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.ent_inc_cat_manage = ttk.Combobox(self.f_incoming, values=self.income_cats, width=30)
        self.ent_inc_cat = self.ent_inc_cat_manage 
        self.ent_inc_cat.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        # OUTGOING
        
                
        # tk.Label(self.f_outgoing, text="Member Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # tk.Label(self.f_outgoing, text="Group:").grid(row=2, column=0, sticky="w"); self.out_grp = ttk.Combobox(self.f_outgoing, values=["Brother", "Sister"], width=22); self.out_grp.grid(row=2, column=1, padx=5, pady=2)
        
        # tk.Label(self.f_outgoing, text="Beneficiary Name:").grid(row=0, column=0, sticky="w"); self.out_ben = ttk.Entry(self.f_outgoing, width=25); self.out_ben.grid(row=0, column=1, padx=5, pady=2)
        # tk.Label(self.f_outgoing, text="Address:").grid(row=0, column=2, sticky="w"); self.out_addr = ttk.Entry(self.f_outgoing, width=25); self.out_addr.grid(row=0, column=3, padx=5, pady=2)
        
        # tk.Label(self.f_outgoing, text="Responsible Person:").grid(row=1, column=0, sticky="w"); self.out_resp = ttk.Combobox(self.f_outgoing, width=22); self.out_resp.grid(row=1, column=1, padx=5, pady=2)
        
        # tk.Label(self.f_outgoing, text="Reason/Note:").grid(row=1, column=2, sticky="w"); self.out_reason = ttk.Entry(self.f_outgoing, width=25); self.out_reason.grid(row=1, column=3, padx=5, pady=2)

        # tk.Label(self.f_outgoing, text="Fund Source:").grid(row=2, column=2, sticky="w"); self.out_fund = ttk.Combobox(self.f_outgoing, values=self.income_cats, width=22); self.out_fund.grid(row=2, column=3, padx=5, pady=2)
        
        tk.Label(self.f_outgoing, text="Beneficiary Name:").grid(row=0, column=0, sticky="w")
        self.out_ben = ttk.Entry(self.f_outgoing, width=25)
        self.out_ben.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(self.f_outgoing, text="Address:").grid(row=0, column=2, sticky="w")
        self.out_addr = ttk.Entry(self.f_outgoing, width=25)
        self.out_addr.grid(row=0, column=3, padx=5, pady=2)
        
        # Responsible Person (Dropdown values will be set dynamically)
        tk.Label(self.f_outgoing, text="Responsible Person:").grid(row=1, column=0, sticky="w")
        self.out_resp = ttk.Combobox(self.f_outgoing, width=22)
        self.out_resp.grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(self.f_outgoing, text="Reason/Note:").grid(row=1, column=2, sticky="w")
        self.out_reason = ttk.Entry(self.f_outgoing, width=25)
        self.out_reason.grid(row=1, column=3, padx=5, pady=2)

        # Group Selection with Event Binding
        tk.Label(self.f_outgoing, text="Group:").grid(row=2, column=0, sticky="w")
        self.out_grp = ttk.Combobox(self.f_outgoing, values=["Brother", "Sister"], width=22)
        self.out_grp.grid(row=2, column=1, padx=5, pady=2)
        self.out_grp.set("Brother") # Set Default
        self.out_grp.bind("<<ComboboxSelected>>", self.update_responsible_dropdown) # <--- NEW BINDING

        tk.Label(self.f_outgoing, text="Fund Source:").grid(row=2, column=2, sticky="w")
        self.out_fund = ttk.Combobox(self.f_outgoing, values=self.income_cats, width=22)
        self.out_fund.grid(row=2, column=3, padx=5, pady=2)
        
        
        tk.Label(self.f_outgoing, text="Usage Type:").grid(row=3, column=0, sticky="w")
        self.ent_out_cat_manage = ttk.Combobox(self.f_outgoing, values=self.outgoing_cats, width=22)
        self.out_use = self.ent_out_cat_manage
        self.out_use.grid(row=3, column=1, padx=5, pady=2)
        self.out_use.bind("<<ComboboxSelected>>", self.check_medical)
        
        self.lbl_med = tk.Label(self.f_outgoing, text="Condition:"); self.ent_med = ttk.Combobox(self.f_outgoing, values=MEDICAL_SUB_TYPES, width=22)

        ttk.Button(main, text="💾 SAVE TRANSACTION", command=self.submit_transaction).pack(pady=20)
        
        
        
        # Last 5
        last5_frame = ttk.LabelFrame(main, text="Last 5 Entries (Double-click to Edit)")
        last5_frame.pack(fill="both", expand=True)
        cols = ("Date", "Type", "Name", "Category", "Amount", "ID")
        self.tree_last5 = ttk.Treeview(last5_frame, columns=cols, show="headings", height=5)
        for c in cols: 
            self.tree_last5.heading(c, text=c)
            if c == "ID": self.tree_last5.column(c, width=0, stretch=False)
            else: self.tree_last5.column(c, width=120)
        self.tree_last5.pack(fill="both", expand=True)
        self.tree_last5.bind("<Double-1>", lambda e: self.open_edit_dialog(self.tree_last5))
        
        self.update_form_view()
        self.update_member_dropdown()

    def update_form_view(self):
        if self.var_type.get() == "Incoming":
            self.f_outgoing.pack_forget()
            self.f_incoming.pack(fill="x", padx=10, pady=5)
            self.update_member_dropdown() # Filter Incoming Member List
        else:
            self.f_incoming.pack_forget()
            self.f_outgoing.pack(fill="x", padx=10, pady=5)
            self.update_responsible_dropdown() # Filter Responsible Person List

    def check_medical(self, event=None):
        if self.out_use.get() == "Medical help": self.lbl_med.grid(row=3, column=2, sticky="w", padx=5); self.ent_med.grid(row=3, column=3, padx=5)
        else: self.lbl_med.grid_remove(); self.ent_med.grid_remove(); self.ent_med.set("")

    def update_member_dropdown(self):
        grp = self.var_inc_grp.get()
        mems = [n for n, d in self.members_db.items() if d.get('group') == grp]
        self.ent_inc_name['values'] = sorted(mems)
    
    def update_responsible_dropdown(self, event=None):
        """Filters Responsible Person list based on Outgoing Group"""
        grp = self.out_grp.get()
        # Find members where 'group' matches the outgoing group selection
        mems = [n for n, d in self.members_db.items() if d.get('group') == grp]
        self.out_resp['values'] = sorted(mems)
        self.out_resp.set('') # Clear previous selection to ensure validity
    
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
                row.update({"Name_Details": self.ent_inc_name.get(), "Group": self.var_inc_grp.get(), "Category": self.ent_inc_cat.get()})
            else:
                fund = self.out_fund.get()
                bal = self.get_fund_balance(fund)
                if amt > bal: return messagebox.showerror("Error", f"Insufficient funds in {fund}")
                row.update({"Name_Details": self.out_ben.get(), "Address": self.out_addr.get(), "Reason": self.out_reason.get(),
                    "Responsible": self.out_resp.get(), "Group": self.out_grp.get(), "Category": fund,
                    "SubCategory": self.out_use.get(), "Medical": self.ent_med.get()})
                
            self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
            self.save_data()
            messagebox.showinfo("Success", "Transaction Saved")
            
        except ValueError: messagebox.showerror("Error", "Invalid Amount")

    # --- UNIVERSAL EDIT DIALOG ---
    def open_edit_dialog(self, tree_widget):
        sel = tree_widget.selection()
        if not sel: return
        values = tree_widget.item(sel[0])['values']
        poss_id = str(values[-1])
        record = self.df[self.df['ID'] == poss_id]
        if record.empty: return
        rec = record.iloc[0]
        
        top = tk.Toplevel(self.root); top.title("Edit Transaction"); top.geometry("500x650")
        f = tk.Frame(top, padx=20, pady=20); f.pack()
        
        tk.Label(f, text=f"EDIT: {rec['Type']}", font=("Arial", 12, "bold")).grid(row=0, columnspan=2, pady=10)
        
        tk.Label(f, text="Date (Y-M-D):").grid(row=1, column=0); e_date = tk.Entry(f); e_date.insert(0, rec['Date']); e_date.grid(row=1, column=1)
        tk.Label(f, text="Amount:").grid(row=2, column=0); e_amt = tk.Entry(f); e_amt.insert(0, rec['Amount']); e_amt.grid(row=2, column=1)
        
        e_name_cb = None; e_cat = None; e_fund = None; e_sub = None; e_med = None; e_addr = None; e_reason = None; e_resp = None; e_name = None
        
        if rec['Type'] == 'Incoming':
            tk.Label(f, text="Member Name:").grid(row=3, column=0)
            e_name_cb = ttk.Combobox(f, values=list(self.members_db.keys()), width=25)
            e_name_cb.set(rec['Name_Details']); e_name_cb.grid(row=3, column=1)
            tk.Label(f, text="Category:").grid(row=4, column=0)
            e_cat = ttk.Combobox(f, values=self.income_cats, width=25); e_cat.set(rec['Category']); e_cat.grid(row=4, column=1)
        else:
            tk.Label(f, text="Beneficiary Name:").grid(row=3, column=0); e_name = tk.Entry(f, width=28); e_name.insert(0, rec['Name_Details']); e_name.grid(row=3, column=1)
            tk.Label(f, text="Fund Source:").grid(row=4, column=0); e_fund = ttk.Combobox(f, values=self.income_cats, width=25); e_fund.set(rec['Category']); e_fund.grid(row=4, column=1)
            tk.Label(f, text="Usage Type:").grid(row=5, column=0); e_sub = ttk.Combobox(f, values=self.outgoing_cats, width=25); e_sub.set(rec['SubCategory']); e_sub.grid(row=5, column=1)
            tk.Label(f, text="Address:").grid(row=6, column=0); e_addr = tk.Entry(f, width=28); e_addr.insert(0, rec['Address']); e_addr.grid(row=6, column=1)
            tk.Label(f, text="Responsible:").grid(row=7, column=0); e_resp = ttk.Combobox(f, values=sorted(list(self.members_db.keys())), width=25); e_resp.set(rec['Responsible']); e_resp.grid(row=7, column=1)
            tk.Label(f, text="Medical:").grid(row=8, column=0); e_med = tk.Entry(f, width=28); e_med.insert(0, rec['Medical']); e_med.grid(row=8, column=1)
            tk.Label(f, text="Reason:").grid(row=9, column=0); e_reason = tk.Entry(f, width=28); e_reason.insert(0, rec['Reason']); e_reason.grid(row=9, column=1)
        
        def save_edit():
            try:
                amt = float(e_amt.get())
                dt = datetime.strptime(e_date.get(), "%Y-%m-%d")
                idx = self.df[self.df['ID'] == rec['ID']].index[0]
                
                self.df.at[idx, 'Amount'] = amt
                self.df.at[idx, 'Date'] = e_date.get()
                self.df.at[idx, 'Year'] = dt.year
                self.df.at[idx, 'Month'] = dt.month
                
                if rec['Type'] == 'Incoming':
                    self.df.at[idx, 'Name_Details'] = e_name_cb.get()
                    self.df.at[idx, 'Category'] = e_cat.get()
                else:
                    self.df.at[idx, 'Name_Details'] = e_name.get()
                    self.df.at[idx, 'Category'] = e_fund.get()
                    self.df.at[idx, 'SubCategory'] = e_sub.get()
                    self.df.at[idx, 'Address'] = e_addr.get()
                    self.df.at[idx, 'Responsible'] = e_resp.get()
                    self.df.at[idx, 'Medical'] = e_med.get()
                    self.df.at[idx, 'Reason'] = e_reason.get()
                
                self.save_data()
                top.destroy()
                messagebox.showinfo("Updated", "Record updated.")
            except: messagebox.showerror("Error", "Invalid Format")

        def delete_rec():
            if messagebox.askyesno("Delete", "Delete this record?"):
                self.df = self.df[self.df['ID'] != rec['ID']]
                self.save_data()
                top.destroy()

        ttk.Button(f, text="Update", command=save_edit).grid(row=11, column=0, pady=20)
        ttk.Button(f, text="Delete", command=delete_rec).grid(row=11, column=1, pady=20)

    # --- TAB 3: LOG ---
    def setup_log_tab(self):
        f = tk.Frame(self.tab_log); f.pack(fill="x", padx=10, pady=5)
        self.log_yr = ttk.Combobox(f, values=["All"] + YEARS, width=6); self.log_yr.set("All"); self.log_yr.pack(side="left")
        self.log_type = ttk.Combobox(f, values=["All", "Incoming", "Outgoing"], width=10); self.log_type.set("All"); self.log_type.pack(side="left", padx=5)
        ttk.Button(f, text="Refresh", command=self.refresh_tables).pack(side="left")
        
        cols = ("Date", "Type", "Name", "Category", "Sub/Med", "Amount", "ID")
        self.tree_log = ttk.Treeview(self.tab_log, columns=cols, show="headings")
        for c in cols: 
            self.tree_log.heading(c, text=c)
            if c == "ID": self.tree_log.column(c, width=0, stretch=False)
            else: self.tree_log.column(c, width=100)
        self.tree_log.pack(fill="both", expand=True, padx=10)
        self.tree_log.bind("<Double-1>", lambda e: self.open_edit_dialog(self.tree_log))

    def refresh_tables(self):
        # Refresh Log (Newest First)
        for i in self.tree_log.get_children(): self.tree_log.delete(i)
        
        # Sorting
        if not self.df.empty:
            self.df['Date_Obj'] = pd.to_datetime(self.df['Date'], errors='coerce')
            view_df = self.df.sort_values(by='Date_Obj', ascending=False)
        else:
            view_df = self.df

        yr = self.log_yr.get()
        if yr != "All": view_df = view_df[view_df['Year'] == int(yr)]
        if self.log_type.get() != "All": view_df = view_df[view_df['Type'] == self.log_type.get()]
        
        for _, r in view_df.iterrows():
            sub = r['SubCategory'] if r['Type'] == 'Outgoing' else ""
            if r['Medical']: sub += f" ({r['Medical']})"
            self.tree_log.insert("", "end", values=(r['Date'], r['Type'], r['Name_Details'], r['Category'], sub, f"{r['Amount']:.2f}", r['ID']))
        
        self.refresh_donations()
        
        # Refresh Last 5
        for i in self.tree_last5.get_children(): self.tree_last5.delete(i)
        if not self.df.empty:
            latest = self.df.sort_values(by='Date_Obj', ascending=False).head(5)
            for _, r in latest.iterrows():
                 self.tree_last5.insert("", "end", values=(r['Date'], r['Type'], r['Name_Details'], r['Category'], f"{r['Amount']:.2f}", r['ID']))

    # --- TAB 4: DONATION ---
    def setup_donation_tab(self):
        f = tk.Frame(self.tab_don); f.pack(fill="x", padx=10, pady=5)
        ttk.Button(f, text="Refresh", command=self.refresh_tables).pack(side="left")
        cols = ("Date", "Beneficiary", "Category", "Sub", "Amount", "ID")
        self.tree_don = ttk.Treeview(self.tab_don, columns=cols, show="headings")
        for c in cols: 
            self.tree_don.heading(c, text=c)
            if c == "ID": self.tree_don.column(c, width=0, stretch=False)
        self.tree_don.pack(fill="both", expand=True, padx=10)
        self.tree_don.bind("<Double-1>", lambda e: self.open_edit_dialog(self.tree_don))

    def refresh_donations(self):
        for i in self.tree_don.get_children(): self.tree_don.delete(i)
        don_df = self.df[self.df['Type'] == 'Outgoing']
        if not don_df.empty:
            don_df = don_df.sort_values(by='Date_Obj', ascending=False)
            for _, r in don_df.iterrows():
                self.tree_don.insert("", "end", values=(r['Date'], r['Name_Details'], r['Category'], r['SubCategory'], f"{r['Amount']:.2f}", r['ID']))

    # --- TAB 6: ANALYSIS ---
    def setup_analysis_tab(self):
        # --- Filters ---
        ctrl = tk.Frame(self.tab_ana); ctrl.pack(fill="x", padx=10, pady=5)
        tk.Label(ctrl, text="Year:").pack(side="left")
        self.ana_yr = ttk.Combobox(ctrl, values=["All"] + YEARS, width=6); self.ana_yr.set(str(datetime.now().year)); self.ana_yr.pack(side="left", padx=5)
        tk.Label(ctrl, text="Group:").pack(side="left", padx=5)
        self.ana_grp = ttk.Combobox(ctrl, values=["All", "Brother", "Sister"], width=10); self.ana_grp.set("All"); self.ana_grp.pack(side="left", padx=5)
        tk.Label(ctrl, text="Chart:").pack(side="left", padx=5)
        self.ana_chart = ttk.Combobox(ctrl, values=["Income Breakdown", "Donation Usage", "Medical Breakdown"], width=18); self.ana_chart.current(0); self.ana_chart.pack(side="left", padx=5)
        ttk.Button(ctrl, text="🔄 Refresh Analysis", command=self.refresh_analysis_views).pack(side="left", padx=10)

        # --- Top Section: Chart ---
        chart_f = tk.Frame(self.tab_ana, height=250); chart_f.pack(fill="x", padx=10)
        self.fig = Figure(figsize=(5, 2.5), dpi=80); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_f); self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # --- Bottom Section: Paned Tables ---
        table_pane = tk.PanedWindow(self.tab_ana, orient=tk.HORIZONTAL)
        table_pane.pack(fill="both", expand=True, padx=10, pady=5)
       
        f_left = tk.Frame(table_pane); table_pane.add(f_left, stretch="always")
        f_right = tk.Frame(table_pane); table_pane.add(f_right, stretch="always")

        # Table Left: Income Category Breakdown
        tk.Label(f_left, text="Income Category Breakdown (Monthly)", font=("Arial", 10, "bold")).pack(anchor="w")
        cat_cols = ["Month"] + self.income_cats + ["Total"]
        self.tree_ana_cats = ttk.Treeview(f_left, columns=cat_cols, show="headings", height=14)
        for c in cat_cols:
           self.tree_ana_cats.heading(c, text=c[:4] if c in MONTH_NAMES else c)
           self.tree_ana_cats.column(c, width=65, anchor="center")
        self.tree_ana_cats.column("Month", width=80, anchor="w")
        self.tree_ana_cats.pack(fill="both", expand=True)

        # Table Right: Flow Overview
        tk.Label(f_right, text="Incoming vs Outgoing Overview", font=("Arial", 10, "bold")).pack(anchor="w")
        flow_cols = ["Month", "Income", "Outgoing", "Balance"]
        self.tree_ana_flow = ttk.Treeview(f_right, columns=flow_cols, show="headings", height=14)
        for c in flow_cols:
           self.tree_ana_flow.heading(c, text=c)
           self.tree_ana_flow.column(c, width=95, anchor="center")
        self.tree_ana_flow.pack(fill="both", expand=True)
    
    def setup_analysis_tabx(self):
        # --- Filters ---
        ctrl = tk.Frame(self.tab_ana); ctrl.pack(fill="x", padx=10, pady=5)
        tk.Label(ctrl, text="Year:").pack(side="left")
        self.ana_yr = ttk.Combobox(ctrl, values=["All"] + YEARS, width=6); self.ana_yr.set(str(datetime.now().year)); self.ana_yr.pack(side="left", padx=5)
        
        tk.Label(ctrl, text="Group:").pack(side="left", padx=5)
        self.ana_grp = ttk.Combobox(ctrl, values=["All", "Brother", "Sister"], width=10); self.ana_grp.set("All"); self.ana_grp.pack(side="left", padx=5)
        
        # ADD THIS: Re-insert the chart selector to fix the AttributeError
        tk.Label(ctrl, text="Chart:").pack(side="left", padx=5)
        self.ana_chart = ttk.Combobox(ctrl, values=["Income Breakdown", "Donation Usage", "Medical Breakdown"], width=18)
        self.ana_chart.current(0); self.ana_chart.pack(side="left", padx=5)
        
        ttk.Button(ctrl, text="🔄 Refresh Analysis", command=self.refresh_analysis_views).pack(side="left", padx=10)


        # --- Top Section: Charts ---
        chart_f = tk.Frame(self.tab_ana, height=300); chart_f.pack(fill="x", padx=10)
        self.fig = Figure(figsize=(5, 3), dpi=80); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_f); self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)
        
        # --- Bottom Section: Tables ---
        table_frame = tk.Frame(self.tab_ana); table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Helper to create summary tables
        def create_summary_table(parent, title, columns):
            lbl = tk.Label(parent, text=title, font=("Arial", 10, "bold"), fg="darkblue"); lbl.pack(anchor="w")
            tree = ttk.Treeview(parent, columns=columns, show="headings", height=7)
            for c in columns: 
                tree.heading(c, text=c if c in ["Metric", "Category"] else c[:3])
                tree.column(c, width=65, anchor="center")
            tree.column(columns[0], width=120, anchor="w") # First col wider
            tree.pack(fill="x", pady=(0, 10))
            return tree

        cols = ["Category"] + MONTH_NAMES + ["Total", "Average"]
        self.tree_ana_cats = create_summary_table(table_frame, "Income Category Breakdown", cols)
        
        cols_flow = ["Metric"] + MONTH_NAMES + ["Total", "Average"]
        self.tree_ana_flow = create_summary_table(table_frame, "Incoming vs Outgoing Overview", cols_flow)

    def refresh_analysis_views(self):
        if hasattr(self, 'ana_chart'):
           self.plot_analysis()
           self.update_analysis_tables()
    
    def update_analysis_tables(self):
        for tree in [self.tree_ana_cats, self.tree_ana_flow]:
            for i in tree.get_children(): tree.delete(i)
        
        yr, grp = self.ana_yr.get(), self.ana_grp.get()
        df_a = self.df.copy()
        df_a['Amount'] = pd.to_numeric(df_a['Amount'], errors='coerce').fillna(0)
        
        if yr != "All": df_a = df_a[df_a['Year'] == int(yr)]
        if grp != "All": df_a = df_a[df_a['Group'] == grp]

        # Accumulators for Averages
        col_totals_cats = {cat: 0.0 for cat in self.income_cats}
        grand_total_inc = 0.0
        total_flow_inc = 0.0
        total_flow_out = 0.0

        for m_idx, m_name in enumerate(MONTH_NAMES, 1):
            # --- Table 1: Category Row ---
            cat_row = [m_name]
            month_sum = 0
            for cat in self.income_cats:
                val = df_a.loc[(df_a['Type'] == "Incoming") & (df_a['Month'] == m_idx) & (df_a['Category'] == cat), 'Amount'].sum()
                cat_row.append(f"{val:.0f}" if val > 0 else "-")
                col_totals_cats[cat] += val
                month_sum += val
            cat_row.append(f"{month_sum:,.2f}")
            grand_total_inc += month_sum
            self.tree_ana_cats.insert("", "end", values=cat_row)

            # --- Table 2: Flow Row ---
            inc_v = df_a.loc[(df_a['Type'] == "Incoming") & (df_a['Month'] == m_idx), 'Amount'].sum()
            out_v = df_a.loc[(df_a['Type'] == "Outgoing") & (df_a['Month'] == m_idx), 'Amount'].sum()
            self.tree_ana_flow.insert("", "end", values=[m_name, f"{inc_v:,.2f}", f"{out_v:,.2f}", f"{(inc_v - out_v):,.2f}"])
            total_flow_inc += inc_v
            total_flow_out += out_v

        # --- FOOTER: TOTALS ---
        f_cat_tot = ["TOTAL"] + [f"{col_totals_cats[c]:,.0f}" for c in self.income_cats] + [f"{grand_total_inc:,.2f}"]
        self.tree_ana_cats.insert("", "end", values=f_cat_tot, tags=('bold',))
        
        f_flow_tot = ["TOTAL", f"{total_flow_inc:,.2f}", f"{total_flow_out:,.2f}", f"{(total_flow_inc - total_flow_out):,.2f}"]
        self.tree_ana_flow.insert("", "end", values=f_flow_tot, tags=('bold',))

        # --- FOOTER: AVERAGES ---
        f_cat_avg = ["AVERAGE"] + [f"{(col_totals_cats[c]/12):,.0f}" for c in self.income_cats] + [f"{(grand_total_inc/12):,.2f}"]
        self.tree_ana_cats.insert("", "end", values=f_cat_avg, tags=('avg',))
        
        f_flow_avg = ["AVERAGE", f"{(total_flow_inc/12):,.2f}", f"{(total_flow_out/12):,.2f}", f"{((total_flow_inc - total_flow_out)/12):,.2f}"]
        self.tree_ana_flow.insert("", "end", values=f_flow_avg, tags=('avg',))
        
        # Styling
        self.tree_ana_cats.tag_configure('bold', background='#e1e1e1', font=('Arial', 9, 'bold'))
        self.tree_ana_flow.tag_configure('bold', background='#e1e1e1', font=('Arial', 9, 'bold'))
        self.tree_ana_cats.tag_configure('avg', background='#f0f8ff', font=('Arial', 9, 'italic'))
        self.tree_ana_flow.tag_configure('avg', background='#f0f8ff', font=('Arial', 9, 'italic'))
    
    def update_analysis_tables2(self):
        # Clear existing
        for tree in [self.tree_ana_cats, self.tree_ana_flow]:
            for i in tree.get_children(): tree.delete(i)
        
        yr, grp = self.ana_yr.get(), self.ana_grp.get()
        df_a = self.df.copy()
        df_a['Amount'] = pd.to_numeric(df_a['Amount'], errors='coerce').fillna(0)
        
        if yr != "All": df_a = df_a[df_a['Year'] == int(yr)]
        if grp != "All": df_a = df_a[df_a['Group'] == grp]

        # Monthly Row Logic
        grand_total_inc = 0
        grand_total_out = 0

        for m_idx, m_name in enumerate(MONTH_NAMES, 1):
            # --- Table 1: Category Row ---
            cat_row = [m_name]
            month_sum = 0
            for cat in self.income_cats:
                val = df_a.loc[(df_a['Type'] == "Incoming") & (df_a['Month'] == m_idx) & (df_a['Category'] == cat), 'Amount'].sum()
                cat_row.append(f"{val:.0f}" if val > 0 else "-")
                month_sum += val
            cat_row.append(f"{month_sum:,.2f}")
            self.tree_ana_cats.insert("", "end", values=cat_row)

            # --- Table 2: Flow Row ---
            inc_val = df_a.loc[(df_a['Type'] == "Incoming") & (df_a['Month'] == m_idx), 'Amount'].sum()
            out_val = df_a.loc[(df_a['Type'] == "Outgoing") & (df_a['Month'] == m_idx), 'Amount'].sum()
            flow_row = [m_name, f"{inc_val:,.2f}", f"{out_val:,.2f}", f"{(inc_val - out_val):,.2f}"]
            self.tree_ana_flow.insert("", "end", values=flow_row)
            
            grand_total_inc += inc_val
            grand_total_out += out_val

        # Add Summary Totals at bottom
        footer_cats = ["TOTAL"] + [""] * len(self.income_cats) + [f"{grand_total_inc:,.2f}"]
        self.tree_ana_cats.insert("", "end", values=footer_cats, tags=('bold',))
        
        footer_flow = ["TOTAL", f"{grand_total_inc:,.2f}", f"{grand_total_out:,.2f}", f"{(grand_total_inc - grand_total_out):,.2f}"]
        self.tree_ana_flow.insert("", "end", values=footer_flow, tags=('bold',))
        
        self.tree_ana_cats.tag_configure('bold', font=('Arial', 9, 'bold'), background='#eeeeee')
        self.tree_ana_flow.tag_configure('bold', font=('Arial', 9, 'bold'), background='#eeeeee')
            
    
    
    def plot_analysis(self):
        self.ax.clear()
        chart = self.ana_chart.get()
        yr = self.ana_yr.get()
        grp = self.ana_grp.get() # Added Group filter
        
        df_a = self.df.copy()
        df_a['Amount'] = pd.to_numeric(df_a['Amount'], errors='coerce').fillna(0)
        
        if yr != "All": df_a = df_a[df_a['Year'] == int(yr)]
        if grp != "All": df_a = df_a[df_a['Group'] == grp] # Apply Group filter
        
        data = None; title = ""
        if chart == "Income Breakdown":
            data = df_a[df_a['Type'] == "Incoming"].groupby("Category")['Amount'].sum(); title = "Income Sources"
        elif chart == "Donation Usage":
            data = df_a[df_a['Type'] == "Outgoing"].groupby("SubCategory")['Amount'].sum(); title = "Donation Distribution"
        elif chart == "Medical Breakdown":
            out = df_a[df_a['Type'] == "Outgoing"]
            data = out[out['SubCategory'] == "Medical help"].groupby("Medical")['Amount'].sum(); title = "Medical Details"
        
        if data is not None and not data.empty:
            self.ax.pie(data, labels=data.index, autopct='%1.1f%%'); self.ax.set_title(title)
        else: 
            self.ax.text(0.5, 0.5, "No Data for Selection", ha='center')
        self.canvas.draw()

    # --- TAB 7: REPORTS ---
    def setup_report_tab(self):
        f = tk.Frame(self.tab_rep); f.pack(fill="x", padx=10, pady=10)
        tk.Label(f, text="Member:").pack(side="left")
        self.rep_mem = ttk.Combobox(f, width=20); self.rep_mem.pack(side="left", padx=5)
        self.rep_mem.bind("<Button-1>", lambda e: self.update_rep_dropdown())
        tk.Label(f, text="Year:").pack(side="left")
        self.rep_yr = ttk.Combobox(f, values=YEARS, width=6); self.rep_yr.set(str(datetime.now().year)); self.rep_yr.pack(side="left")
        ttk.Button(f, text="Generate PDF", command=self.generate_report_pdf).pack(side="left", padx=20)
        
        msg_frame = tk.LabelFrame(self.tab_rep, text="PDF Messages")
        msg_frame.pack(fill="x", padx=10)
        self.txt_header = tk.Text(msg_frame, height=20); self.txt_header.pack(fill="x"); self.txt_header.insert("1.0", "We appreciate your contribution.")
        self.txt_footer = tk.Text(msg_frame, height=20); self.txt_footer.pack(fill="x"); self.txt_footer.insert("1.0", "Contact admin for queries.")

    def update_rep_dropdown(self):
        mems = sorted(list(self.members_db.keys()))
        self.rep_mem['values'] = mems

    # --- HELPER: PIE CHART FOR PDF ---
    def create_pie_chart_image(self, data_series, title):
        if data_series.empty: return None
        fig = Figure(figsize=(5, 5), dpi=300)
        ax = fig.add_subplot(111)
        ax.pie(data_series, labels=data_series.index, autopct='%1.1f%%')
        ax.set_title(title)
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format='png')
        img_buf.seek(0)
        return Image(img_buf, width=3*inch, height=3*inch)
    
    def generate_report_pdf(self):
        if not HAS_PDF: return messagebox.showerror("Error", "ReportLab not installed")
        name = self.rep_mem.get(); year = int(self.rep_yr.get())
        if not name: return
        
        # 1. Filter Incoming Data for Member (Make a copy to avoid warnings)
        mdf = self.df[(self.df['Name_Details'] == name) & (self.df['Type'] == 'Incoming') & (self.df['Year'] == year)].copy()
        
        # 2. Get Member Info
        mem_info = self.members_db.get(name, {})
        
        # --- FIX: Use the 'joined' date from member profile, not calculated from transactions ---
        mem_since = mem_info.get('joined', 'N/A') 
        
        # Calculate Lifetime Total
        lifetime_total = self.df[(self.df['Name_Details'] == name) & (self.df['Type'] == 'Incoming')]['Amount'].sum()

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
            highlight_style = ParagraphStyle('Highlight', parent=styles['Normal'], fontSize=12, textColor=colors.darkblue)

            # Header
            elements.append(Paragraph("Bismillah hir Rahmanir Rahim", header_style))
            elements.append(Paragraph("Sadaka Group Berlin", title_style))
            elements.append(Paragraph("Member Contribution Report", styles['Heading2']))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(QURAN_QUOTE, quote_style)); elements.append(Paragraph(HADITH_QUOTE, quote_style)); elements.append(Spacer(1, 15))
            
            # Profile
            elements.append(Paragraph(f"<b>Member:</b> {name}", styles['Normal']))
            elements.append(Paragraph(f"<b>Member Since:</b> {mem_since}", styles['Normal'])) # <--- Now uses the correct variable
            elements.append(Paragraph(f"<b>Details:</b> {mem_info.get('address','-')} | {mem_info.get('phone','-')}", styles['Normal']))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>LIFETIME TOTAL: {CURRENCY}{lifetime_total:,.2f}</b>", highlight_style))
            elements.append(Spacer(1, 15))
            
            elements.append(Paragraph(self.txt_header.get("1.0", "end-1c"), styles['Italic'])); elements.append(Spacer(1, 15))
            
            # Table 1: Contributions
            elements.append(Paragraph(f"1. Contributions in {year}", styles['Heading3']))
            data1 = [["Date", "Category", "Amount"]]; total = 0
            
            if not mdf.empty:
                # Sort by date properly
                mdf['Date_Obj'] = pd.to_datetime(mdf['Date'], errors='coerce')
                mdf = mdf.sort_values(by='Date_Obj')
                
                for _, r in mdf.iterrows():
                    data1.append([r['Date'], r['Category'], f"{r['Amount']:.2f}"])
                    total += r['Amount']
            
            data1.append(["", "TOTAL:", f"{total:.2f}"])
            t1 = Table(data1, colWidths=[100, 150, 100]); t1.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.darkgreen), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]))
            elements.append(t1); elements.append(Spacer(1, 20))
            
            # Table 2: Donations Distributed
            grp = mem_info.get('group', 'Brother')
            don_df = self.df[(self.df['Type'] == 'Outgoing') & (self.df['Year'] == year) & (self.df['Group'] == grp)].copy()
            
            if not don_df.empty:
                don_df['Date_Obj'] = pd.to_datetime(don_df['Date'], errors='coerce')
                don_df = don_df.sort_values(by='Date_Obj')
            
            elements.append(Paragraph(f"2. Donations Distributed ({grp}s)", styles['Heading3']))
            data2 = [["Date", "Beneficiary", "Reason", "Responsible", "Amount"]]
            d_total = 0
            for _, r in don_df.iterrows():
                data2.append([r['Date'], r['Name_Details'], r['Reason'], r['Responsible'], f"{r['Amount']:.2f}"])
                d_total += r['Amount']
            data2.append(["", "", "", "TOTAL:", f"{d_total:.2f}"])
            
            t2 = Table(data2, colWidths=[60, 100, 100, 80, 60]); t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('FONTSIZE', (0,0), (-1,-1), 8)]))
            elements.append(t2)
            elements.append(Spacer(1, 20))
            
            # Table 3: Overall Summary for Group
            elements.append(Paragraph(f"3. {grp}s Group Summary ({year})", styles['Heading3']))
            
            # Get Group Summary Data
            group_inc = self.df[(self.df['Type'] == 'Incoming') & (self.df['Year'] == year) & (self.df['Group'] == grp)].copy()
            
            summary_data = [["Month", "Income", "Donation", "Balance"]]
            
            # Calculate Monthly Stats for PDF Table
            monthly_stats = {m: {'inc': 0.0, 'don': 0.0} for m in range(1, 13)}
            
            # Fill Income
            if not group_inc.empty:
                inc_grp = group_inc.groupby('Month')['Amount'].sum()
                for m, val in inc_grp.items():
                    if m in monthly_stats: monthly_stats[m]['inc'] = val
            
            # Fill Donation (using don_df calculated earlier)
            if not don_df.empty:
                don_grp = don_df.groupby('Month')['Amount'].sum()
                for m, val in don_grp.items():
                    if m in monthly_stats: monthly_stats[m]['don'] = val

            total_inc = 0; total_don = 0; total_bal = 0
            
            for m in range(1, 13):
                inc = monthly_stats[m]['inc']
                don = monthly_stats[m]['don']
                bal = inc - don
                summary_data.append([MONTH_NAMES[m-1], f"{inc:.2f}", f"{don:.2f}", f"{bal:.2f}"])
                total_inc += inc
                total_don += don
                total_bal += bal
                
            summary_data.append(["TOTAL", f"{total_inc:.2f}", f"{total_don:.2f}", f"{total_bal:.2f}"])
            
            t3 = Table(summary_data, colWidths=[100, 80, 80, 80])
            t3.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.navy), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]))
            elements.append(t3)
            elements.append(Spacer(1, 20))
            
            # Charts
            elements.append(Paragraph(f"4. Analysis Charts ({year})", styles['Heading3']))
            
            # Fund Source Chart
            fund_stats = don_df.groupby("Category")['Amount'].sum()
            img_fund = self.create_pie_chart_image(fund_stats, "By Fund Source")
            
            # Usage Chart
            usage_stats = don_df.groupby("SubCategory")['Amount'].sum()
            img_usage = self.create_pie_chart_image(usage_stats, "By Usage")
            
            # Medical Chart
            med_df = don_df[don_df['SubCategory'] == "Medical help"]
            img_med = None
            if not med_df.empty:
                med_stats = med_df.groupby("Medical")['Amount'].sum()
                img_med = self.create_pie_chart_image(med_stats, "Medical Breakdown")

            if img_fund and img_usage:
                chart_table_1 = Table([[img_fund, img_usage]], colWidths=[3.5*inch, 3.5*inch])
                elements.append(chart_table_1)
            
            if img_med:
                chart_table_2 = Table([[img_med]], colWidths=[7*inch]); chart_table_2.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
                elements.append(chart_table_2)
            
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
    
    
            
            
    

    # --- TAB 1: MEMBER MANAGEMENT (WITH RENAME FIX) ---
    def setup_member_tab(self):
        paned = tk.PanedWindow(self.tab_mem, orient=tk.HORIZONTAL); paned.pack(fill="both", expand=True, padx=10, pady=10)
        left_f = tk.LabelFrame(paned, text="Register / Edit Member", padx=10, pady=10)
        right_f = tk.LabelFrame(paned, text="Registered Members List", padx=10, pady=10)
        paned.add(left_f, width=400); paned.add(right_f)
        
        tk.Label(left_f, text="Full Name:").pack(anchor="w"); self.mem_name = ttk.Entry(left_f); self.mem_name.pack(fill="x")
        tk.Label(left_f, text="Member ID (Optional):").pack(anchor="w"); self.mem_id = ttk.Entry(left_f); self.mem_id.pack(fill="x")
        tk.Label(left_f, text="Group:").pack(anchor="w", pady=(10, 0)); self.mem_grp = tk.StringVar(value="Brother"); ttk.Radiobutton(left_f, text="Brother", variable=self.mem_grp, value="Brother").pack(anchor="w"); ttk.Radiobutton(left_f, text="Sister", variable=self.mem_grp, value="Sister").pack(anchor="w")
        tk.Label(left_f, text="Phone:").pack(anchor="w", pady=(10,0)); self.mem_phone = ttk.Entry(left_f); self.mem_phone.pack(fill="x")
        tk.Label(left_f, text="Email:").pack(anchor="w"); self.mem_email = ttk.Entry(left_f); self.mem_email.pack(fill="x")
        tk.Label(left_f, text="Address:").pack(anchor="w"); self.mem_addr = ttk.Entry(left_f); self.mem_addr.pack(fill="x")
        tk.Label(left_f, text="Date Joined:").pack(anchor="w"); self.mem_date = ttk.Entry(left_f); self.mem_date.pack(fill="x"); self.mem_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        btn_f = tk.Frame(left_f); btn_f.pack(pady=20, fill="x"); ttk.Button(btn_f, text="Save / Update", command=self.save_member).pack(side="left", fill="x", expand=True); ttk.Button(btn_f, text="Delete", command=self.delete_member).pack(side="right", fill="x", expand=True)

        cols = ("Name", "ID", "Group", "Phone", "Email")
        self.tree_mems = ttk.Treeview(right_f, columns=cols, show="headings")
        for c in cols: self.tree_mems.heading(c, text=c)
        self.tree_mems.column("Name", width=120)
        self.tree_mems.pack(fill="both", expand=True)
        self.tree_mems.bind("<Double-1>", self.load_member_to_edit)
        self.refresh_member_list_tab()

    def load_member_to_edit(self, event):
        sel = self.tree_mems.selection()
        if not sel: return
        name = self.tree_mems.item(sel[0])['values'][0]
        data = self.members_db.get(name, {})
        
        # Track original name for rename
        self.editing_member_original_name = name
        
        self.mem_name.delete(0, tk.END); self.mem_name.insert(0, name)
        self.mem_id.delete(0, tk.END); self.mem_id.insert(0, data.get('id', ''))
        self.mem_grp.set(data.get('group', 'Brother'))
        self.mem_phone.delete(0, tk.END); self.mem_phone.insert(0, data.get('phone', ''))
        self.mem_email.delete(0, tk.END); self.mem_email.insert(0, data.get('email', ''))
        self.mem_addr.delete(0, tk.END); self.mem_addr.insert(0, data.get('address', ''))
        self.mem_date.delete(0, tk.END); self.mem_date.insert(0, data.get('joined', ''))

        
    def save_member(self):
        name = self.mem_name.get().strip()
        if not name: return messagebox.showerror("Error", "Name required")
        
        mid = self.mem_id.get().strip()
        if not mid: 
            # If creating new or editing existing without ID, keep existing ID or create new
            mid = self.members_db.get(name, {}).get("id", str(uuid.uuid4())[:8])

        # FIX: Ensure 'joined' reads from the Entry field (self.mem_date.get())
        self.members_db[name] = {
            "id": mid,
            "group": self.mem_grp.get(), 
            "phone": self.mem_phone.get(), 
            "email": self.mem_email.get(), 
            "address": self.mem_addr.get(), 
            "joined": self.mem_date.get()  # <--- Crucial: Reads the text box value
        }
        
        self.save_members()
        self.refresh_member_list_tab()
        
        # Clear fields
        self.mem_name.delete(0, tk.END)
        self.mem_id.delete(0, tk.END)
        self.mem_phone.delete(0, tk.END)
        self.mem_email.delete(0, tk.END)
        self.mem_addr.delete(0, tk.END)
        self.mem_date.delete(0, tk.END)
        self.mem_date.insert(0, datetime.now().strftime("%Y-%m-%d")) # Reset date to today
        
        messagebox.showinfo("Success", "Member Saved")

    def delete_member(self):
        name = self.mem_name.get().strip()
        if name in self.members_db: 
            if messagebox.askyesno("Confirm", "Delete member and keep history?"):
                del self.members_db[name]
                self.save_members()
                self.refresh_all_views()
                self.mem_name.delete(0, tk.END)

    def refresh_member_list_tab(self):
        for i in self.tree_mems.get_children(): self.tree_mems.delete(i)
        for name, data in self.members_db.items():
            self.tree_mems.insert("", "end", values=(name, data.get("id"), data.get("group"), data.get("phone"), data.get("email")))

    # --- TAB 7: MATRIX ---
    def setup_overall_contribution_tab(self):
        ctrl = tk.Frame(self.tab_matrix); ctrl.pack(fill="x", padx=10, pady=5)
        tk.Label(ctrl, text="Filter Year:").pack(side="left")
        self.matrix_yr = ttk.Combobox(ctrl, values=["All"] + YEARS, width=6); self.matrix_yr.set("All"); self.matrix_yr.pack(side="left", padx=5)
        tk.Label(ctrl, text="Group:").pack(side="left", padx=10)
        self.matrix_grp = ttk.Combobox(ctrl, values=["All", "Brother", "Sister"], width=8); self.matrix_grp.set("All"); self.matrix_grp.pack(side="left", padx=5)
        
        tk.Label(ctrl, text="Category:").pack(side="left", padx=5)
        self.matrix_cat = ttk.Combobox(ctrl, values=["All"] + self.income_cats, width=12); self.matrix_cat.set("All"); self.matrix_cat.pack(side="left", padx=5) 
        ttk.Button(ctrl, text="Load / Refresh", command=self.generate_matrix_report).pack(side="left", padx=20)
        
        cols = ["Name"] + MONTH_NAMES + ["TOTAL"]
        self.tree_matrix = ttk.Treeview(self.tab_matrix, columns=cols, show="headings", height=20)
        self.tree_matrix.heading("Name", text="Member Name"); self.tree_matrix.column("Name", width=150, anchor="w")
        for m in MONTH_NAMES: self.tree_matrix.heading(m, text=m[:3]); self.tree_matrix.column(m, width=60, anchor="center")
        self.tree_matrix.heading("TOTAL", text="Total"); self.tree_matrix.column("TOTAL", width=80, anchor="e")
        self.tree_matrix.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        vsb = ttk.Scrollbar(self.tab_matrix, orient="vertical", command=self.tree_matrix.yview)
        self.tree_matrix.configure(yscrollcommand=vsb.set); vsb.pack(side="right", fill="y", pady=5)

    def generate_matrix_report(self):
        for i in self.tree_matrix.get_children(): self.tree_matrix.delete(i)
        yr, grp, cat = self.matrix_yr.get(), self.matrix_grp.get(), self.matrix_cat.get()
        
        data = self.df[self.df['Type'] == 'Incoming'].copy()
        data['Amount'] = pd.to_numeric(data['Amount'], errors='coerce').fillna(0)
        
        if yr != "All": data = data[data['Year'] == int(yr)]
        if grp != "All": data = data[data['Group'] == grp]
        # --- APPLY CATEGORY FILTER ---
        if cat != "All": data = data[data['Category'] == cat]
        
        if data.empty: return
        pivot = data.pivot_table(index="Name_Details", columns="Month", values="Amount", aggfunc="sum", fill_value=0)
        monthly_totals = {m: 0.0 for m in range(1, 13)}; grand_total = 0.0
        for name, row in pivot.iterrows():
            values = [name]; row_total = 0.0
            for m_num in range(1, 13):
                val = row.get(m_num, 0.0); values.append(f"{val:.0f}" if val > 0 else "-"); row_total += val; monthly_totals[m_num] += val
            values.append(f"{row_total:,.2f}"); grand_total += row_total
            self.tree_matrix.insert("", "end", values=values)
        footer = ["GRAND TOTAL"]
        for m_num in range(1, 13): footer.append(f"{monthly_totals[m_num]:,.0f}")
        footer.append(f"{grand_total:,.2f}")
        self.tree_matrix.insert("", "end", values=footer, tags=('bold',)); self.tree_matrix.tag_configure('bold', font=('Arial', 10, 'bold'), background='#e1e1e1')

if __name__ == "__main__":
    root = tk.Tk()
    app = CharityApp(root)
    root.mainloop()
