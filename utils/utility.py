import streamlit as st

import pandas as pd
import random
from datetime import datetime

from io import StringIO
import re
from typing import List, Optional, Dict, Any
from fuzzywuzzy import process

from supabase import create_client
from utils.globals import COLUMN_SORT_ORDER

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

    
def get_lookup(
    table: str, 
    filters: Optional[Dict[str, Any]]=None, 
    distinct: Optional[str]=None
):
    """
    Get back a row from supabase or a list of unique values. 
    table: Supabase table name. Note the global anon key is loaded inside. 
    filters: column equals value dict pair. DOES NOT SUPPORT LIST VALUE. 

    Usage: 
      get_lookup(table='s1mc_v2', filters={'id': 38}) >> [{'id': '38', ... ]
      get_lookup(table='s1mc_v2', distinct='year) >> [2020, 2019...]
    """
    url = supabase_url
    key = supabase_anon_key
    supabase = create_client(url, key)
    
    if distinct:
        query_builder = supabase.table(table).select(distinct)
    else:
        query_builder = supabase.table(table).select('*')
        
    if filters:
        for column, value in filters.items():
            query_builder = query_builder.filter(column, 'eq', value)
    
    try:
        response = query_builder.execute()
        data = response.data
        if distinct:
            unique_values = list(set(row[distinct] for row in data))
            return unique_values
        return data
    
    except Exception as e:
        raise e


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

#-------
# Helper for download export
#---------
@st.cache_data
def convert_df(df):
  return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_warnings(warnings: List):
  warnings_str = "\n".join(warnings)
  return warnings_str

#---
# Model Helpers
#---
def convert_BaseModel(cls, examples:bool=False, return_as_string:bool=True):
  """ 
  cls: Must be pydantic basemodel class
  examples: If True, return header + 5 rows of examples. If False, return only header row
  get_as_string: If True, return str representation of csv. If False, return pd DataFrame.
  """
  if not examples:
    field_names = list(cls.model_fields.keys())
    if 'uuid' in field_names:
       field_names.remove('uuid')
    df = pd.DataFrame(columns=field_names)
  
  else:
    def random_value_for_type(field_type):
      if field_type == str:
        return 'EXAMPLE_' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=5))
      elif field_type == float:
        return random.uniform(1, 100)
      elif field_type == int:
        return random.randint(1, 100)
      elif field_type == bool:
        return random.choice(['True', 'False'])
      elif field_type == datetime:
        return datetime.now().strftime('%Y-%m-%d')
      else:
        return '<Blank>'

    def create_random_row(cls):
      row = {}
      for field_name, field_info in cls.model_fields.items():  # pydantic only
        if field_name == 'uuid':  # Skip uuid field
          continue

        field_type = field_info.annotation
        default_value = str(field_info.default) # str representation to catch PydanticUndefined
  
        # Check if a default value exists and is not None or Undefined
        if default_value not in ['None', 'PydanticUndefined']:
          row[field_name] = default_value
        else:
          row[field_name] = random_value_for_type(field_type) if default_value in ['None', 'PydanticUndefined'] else '<Blank>'
      return row

    field_names = list(cls.model_fields.keys())
    if 'uuid' in field_names:
      field_names.remove('uuid')    
    df = pd.DataFrame(columns=field_names)
    
    # Add example rows
    for _ in range(5):
      example_row = create_random_row(cls)
      df = pd.concat([df, pd.DataFrame([example_row])], axis=0)

  # Sort columns according to globals
  df = df[[col for col in COLUMN_SORT_ORDER if col in df.columns]] 
    
  if return_as_string:
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_str = csv_buffer.getvalue()
    return csv_str
  return df

@st.cache_data 
def get_cached_df(BaseModelCls): # cache still doesnt work with aggrid
  return convert_BaseModel(BaseModelCls, examples=True, return_as_string=False)


