import streamlit as st
import pandas as pd
import re

#-----------------------
# Helper functions
#-----------------------
@st.cache_data
def get_dataframe(data):
  return pd.DataFrame(data)

def clean_text(text):
  clean_text = re.sub(r'[^a-zA-Z0-9_,.:\s\[\]]', ' ', text)
  return clean_text

