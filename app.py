import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="Email Delivery Dashboard",
    page_icon="🚀",
    layout="wide"
)

# --- Hard-coded File Paths and Column Names ---
# The app will look for these files in the same directory.
ORIGINAL_FILE_PATH = 'soai_l1_all_cohorts.csv'
SUCCESSFUL_FILE_PATH = 'total_successfull.csv'
ORIGINAL_EMAIL_COL = 'email'  # Adjust if your column name is different
SUCCESSFUL_EMAIL_COL = 'email' # Adjust if your column name is different


# --- Data Loading and Processing Function ---
@st.cache_data # This is a powerful Streamlit feature!
def load_and_process_data():
    """
    This function loads data from local CSVs, cleans it, and performs the analysis.
    The @st.cache_data decorator means it only runs ONCE, making the app super fast.
    """
    try:
        df_orig = pd.read_csv(ORIGINAL_FILE_PATH)
        df_succ = pd.read_csv(SUCCESSFUL_FILE_PATH)
    except FileNotFoundError as e:
        st.error(f"Fatal Error: File not found -> '{e.filename}'.")
        st.error("Please make sure both 'soai_l1_all_cohorts.csv' and 'total_successfull.csv' are in the same folder as the app.")
        return None # Return None to indicate failure

    # --- Data Cleaning and Accurate Calculations ---
    # Clean and get unique emails from the original list
    df_orig['clean_email'] = df_orig[ORIGINAL_EMAIL_COL].str.strip().str.lower()
    df_orig.drop_duplicates(subset=['clean_email'], inplace=True, keep='first')

    # Create a fast lookup set for successful emails
    df_succ['clean_email'] = df_succ[SUCCESSFUL_EMAIL_COL].str.strip().str.lower()
    successful_emails_set = set(df_succ['clean_email'])
    
    # Find undelivered contacts
    undelivered_mask = ~df_orig['clean_email'].isin(successful_emails_set)
    df_undelivered = df_orig[undelivered_mask]
    
    # Calculate final counts based on unique contacts
    total_unique_count = len(df_orig)
    undelivered_count = len(df_undelivered)
    successful_count = total_unique_count - undelivered_count
    
    # Return all the necessary data in a dictionary
    return {
        "total_unique": total_unique_count,
        "successful": successful_count,
        "undelivered": undelivered_count,
        "undelivered_df": df_undelivered,
        "original_email_col": ORIGINAL_EMAIL_COL
    }

# --- Main App ---
st.title("🚀 Automatic Email Delivery Dashboard")

# Load and process the data automatically on startup.
processed_data = load_and_process_data()

# Only display the dashboard if the data was loaded successfully.
if processed_data:
    st.header("📈 Delivery Summary")
    
    # --- Metrics and Visualization ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Unique Contacts", f"{processed_data['total_unique']:,}")
        st.metric("✅ Successful Deliveries", f"{processed_data['successful']:,}")
        st.metric("❌ Undelivered / Bounced", f"{processed_data['undelivered']:,}", delta_color="inverse")

    with col2:
        fig = go.Figure(data=[go.Pie(
            labels=['Successful', 'Undelivered'],
            values=[processed_data['successful'], processed_data['undelivered']],
            marker_colors=['#28a745', '#dc3545'],
            hole=.4
        )])
        fig.update_layout(title_text="Delivery Status Overview")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Email Lookup Tool ---
    st.header("🔍 Email Status Lookup")
    email_to_check = st.text_input("Enter an email address to check its delivery status:", placeholder="example@domain.com")

    if email_to_check:
        undelivered_df = processed_data['undelivered_df']
        # Check against the 'clean_email' column for accuracy
        if email_to_check.strip().lower() in undelivered_df['clean_email'].values:
            st.error(f"**Status: ❌ Not Delivered** - '{email_to_check}' is on the undelivered list.")
        else:
            st.success(f"**Status: ✅ Delivered** - '{email_to_check}' was successfully delivered (or was not in your original contact list).")
    
    st.divider()
    
    # --- Undelivered List Display ---
    with st.expander("📂 View Full List of Undelivered Contacts"):
        undelivered_df_display = processed_data['undelivered_df'][[processed_data['original_email_col']]]
        st.dataframe(undelivered_df_display)
        
        st.download_button(
            label="📥 Download Undelivered List as CSV",
            data=undelivered_df_display.to_csv(index=False).encode('utf-8'),
            file_name='undelivered_contacts.csv',
            mime='text/csv',
        )