import streamlit as st
from utils.charting import initialize_plotly_themes

def run_app_config():
  st.session_state['app_configurated'] = True

  # Inits
  initialize_plotly_themes()
  
  if 's3vc_df' not in st.session_state: 
    st.session_state['s3vc_df'] = None
  if 's3vc_original_dfs' not in st.session_state:
      st.session_state['s3vc_original_dfs'] = {}
  if 's3vc_dfs' not in st.session_state:
      st.session_state['s3vc_dfs'] = {}
  if 's3vc_warnings' not in st.session_state:
      st.session_state['s3vc_warnings'] = {}
  if 's3vc_calc_results' not in st.session_state:
      st.session_state['s3vc_calc_results'] = {}
  if 'analyzed_s3vc' not in st.session_state:
      st.session_state['analyzed_s3vc'] = False