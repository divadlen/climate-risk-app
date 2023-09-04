import streamlit as st
import pandas as pd
from io import StringIO

import re
from typing import List, Optional
from fuzzywuzzy import process
from supabase import create_client

supabase_url= st.secrets['supabase_url']
supabase_anon_key= st.secrets['supabase_anon_key']
supabase = create_client(supabase_url, supabase_anon_key)

#-----------------------
# Helper functions
#-----------------------

def supabase_query(table:str, url:str, key:str, limit: Optional[int]=10000):
    supabase = create_client(url, key)
    query_builder = supabase.table(table).select("*")
    if limit is not None:
        query_builder = query_builder.limit(limit)

    try:
        response = query_builder.execute()
    except Exception as e:
        raise e

    if response.data in ([], None):
        print(f'No data found for `{table}`. Make sure RLS is turned off.')
    return response.data


@st.cache_data
def get_dataframe(data):
  return pd.DataFrame(data)


def clean_text(text):
  clean_text = re.sub(r'[^a-zA-Z0-9_,.:\s\[\]]', ' ', text)
  return clean_text


def find_closest_category(input_str, allowed_list:list, threshold=80, abbrv_dict: dict={}):
    """
    Autocorrect for a list of options
    abbrv_dict: 
      Dictionary containing custom pairs. EG: 'usa': 'United States of America'
      Useful if fuzzy matching is returning unintentional results
    """
    if input_str in [None, '']:
        return None

    if abbrv_dict not in [None, {}]:
        input_str = abbrv_dict.get(input_str.strip().lower(), input_str)
    
    closest_match, score = process.extractOne(input_str, allowed_list)
    if score >= threshold:
        return closest_match
    else:
        return None 


#--Helper for download export--#
@st.cache_data
def convert_df(df):
  return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_warnings(warnings: List):
  warnings_str = "\n".join(warnings)
  return warnings_str

def convert_BaseModel(model_class) -> str:
  field_names = list(model_class.__annotations__.keys())

  if 'uuid' in field_names:
    field_names.remove('uuid')
    
  df = pd.DataFrame(columns=field_names)
  csv_buffer = StringIO()
  df.to_csv(csv_buffer, index=False)
  csv_str = csv_buffer.getvalue()
  return csv_str
                    
                  
