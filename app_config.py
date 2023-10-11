import streamlit as st
from PIL import Image
from utils.charting import initialize_plotly_themes

def run_app_config():
  st.session_state['app_configurated'] = True

  # Inits
  if 'theme_choice' not in st.session_state:
    st.session_state.theme_choice = 'Light'
  if 'theme_colors' not in st.session_state:
    st.session_state.theme_colors = {}
  
  if 'watermark_settings' not in st.session_state:
    st.session_state.watermark_settings = [dict(
      source= Image.open("./resources/BlackShortText_Logo_Horizontal-long.png"),
      xref="paper", yref="paper",
      x=0.985, y=0.015,
      sizex=0.012, sizey=0.012, opacity= 0.15,
      xanchor="right", yanchor="bottom"
  )]

  initialize_plotly_themes()

  if 's1de_calc_results' not in st.session_state:
    st.session_state['s1de_calc_results'] = {}

  if 's2ie_calc_results' not in st.session_state:
    st.session_state['s2ie_calc_results'] = {}

  if 's3vc_calc_results' not in st.session_state:
    st.session_state['s3vc_calc_results'] = {}


  
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