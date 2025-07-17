import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="Advanced Email Diagnostics",
    page_icon="🔬",
    layout="wide"
)

# --- File Configuration ---
# We now only need 4 files. The app will derive the upload failures.
CONFIG = {
    "original":   {"path": "soai_l1_all_cohorts.csv", "col": "email"},
    "successful": {"path": "total_successfull.csv",   "col": "email"},
    "soft_bounce":{"path": "soft_bounces.csv",        "col": "email"},
    "hard_bounce":{"path": "hard_bounces.csv",        "col": "email"}
}


# --- Data Loading and Analysis Function ---
@st.cache_data
def load_and_diagnose_data():
    """
    Loads all data, cleans it, and assigns a detailed status to each contact,
    deriving the "Upload Failure" category automatically.
    """
    dataframes = {}
    try:
        for key, info in CONFIG.items():
            dataframes[key] = pd.read_csv(info["path"])
    except FileNotFoundError as e:
        st.error(f"Fatal Error: File not found -> '{e.filename}'.")
        st.error(f"Please make sure all required CSV files are in the same folder as the app.")
        return None

    # --- Create fast lookup sets for each category ---
    sets = {}
    for key, df in dataframes.items():
        col_name = CONFIG[key]["col"]
        if col_name in df.columns:
            # Drop NaN values before converting to set
            sets[key] = set(df[col_name].dropna().str.strip().str.lower())
        else:
            st.error(f"Column '{col_name}' not found in '{CONFIG[key]['path']}'")
            return None
            
    # The original list is our "universe" of contacts
    df_orig = dataframes["original"]
    df_orig['clean_email'] = df_orig[CONFIG["original"]["col"]].str.strip().str.lower()
    df_orig.drop_duplicates(subset=['clean_email'], inplace=True, keep='first')

    # --- Categorization Logic with a clear hierarchy ---
    def get_status(email):
        if email in sets["successful"]:
            return "Successful"
        if email in sets["hard_bounce"]:
            return "Hard Bounce"
        if email in sets["soft_bounce"]:
            return "Soft Bounce"
        # If an email is not in any of the outcome lists (successful, bounced),
        # it must have failed to upload into the system. We derive this status.
        return "Upload Failure (Derived)"

    # Apply the logic to create a new 'status' column
    df_orig['status'] = df_orig['clean_email'].apply(get_status)
    return df_orig


# --- Main App UI ---
st.title("🔬 Advanced Email Delivery Diagnostics")
st.markdown("This dashboard analyzes your campaign results to categorize every contact, including deriving upload failures.")

# Load and process the data on startup
final_report = load_and_diagnose_data()

if final_report is not None:
    status_counts = final_report['status'].value_counts()

    st.header("📈 Overall Campaign Summary")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        total = len(final_report)
        successful = status_counts.get("Successful", 0)
        failures = total - successful
        
        st.metric("Total Unique Contacts", f"{total:,}")
        st.metric("✅ Successful Deliveries", f"{successful:,}")
        st.metric("❌ Total Failures", f"{failures:,}")

    with col2:
        fig = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=.4,
            textinfo='label+percent',
            insidetextorientation='radial'
        )])
        fig.update_layout(title_text="Delivery Status Breakdown", legend_title_text='Status')
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Email Lookup Tool ---
    st.header("🔍 Individual Email Status Lookup")
    email_to_check = st.text_input("Enter an email address to check its detailed status:", placeholder="example@domain.com")

    if email_to_check:
        clean_email = email_to_check.strip().lower()
        result = final_report[final_report['clean_email'] == clean_email]

        if not result.empty:
            status = result.iloc[0]['status']
            if status == "Upload Failure (Derived)":
                st.error(f"**Status: ❌ Upload Failure (Derived)** - This email was in your original list but was not found in any of the delivery or bounce reports from Brevo.")
            elif status == "Successful":
                 st.success(f"**Status: ✅ {status}** - This contact received the email successfully.")
            else:
                st.warning(f"**Status: ❌ {status}** - This contact did not receive the email due to a bounce.")
        else:
            st.info(f"**Status: Can't Find** - The email '{email_to_check}' was not found in the original contact list.")

    st.divider()
    
    # --- Full Report Display ---
    with st.expander("📂 View and Download Full Diagnostic Report"):
        report_to_display = final_report[[CONFIG["original"]["col"], 'status']].rename(columns={CONFIG["original"]["col"]: "Email"})
        st.dataframe(report_to_display)
        
        st.download_button(
            label="📥 Download Full Report as CSV",
            data=report_to_display.to_csv(index=False).encode('utf-8'),
            file_name='full_delivery_diagnostics.csv',
            mime='text/csv',
        )