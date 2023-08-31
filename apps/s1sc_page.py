import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from stqdm import stqdm

import numpy as np
import pandas as pd
import logging
import random
import json
from typing import List
from supabase import create_client

import plotly.express as px

from utils.s1sc_FuelData import create_fuel_data, S1SC_Lookup_Cache, FuelData, FuelCalculatorTool
from utils.utility import get_dataframe

# Instantiate cache for emission lookup and state lookup


def s1sc_Page():
  if 'S1SC_Lookup_Cache' not in st.session_state:
    st.session_state['S1SC_Lookup_Cache'] = S1SC_Lookup_Cache()
  if 's1sc_df' not in st.session_state: #
    st.session_state['s1sc_df'] = None
  if 'validated_s1sc_df' not in st.session_state:
    st.session_state['validated_s1sc_df'] = None
    st.session_state['validated_s1sc_warnings'] = []


  st.title('Stationary Combustion')
  tab1, tab2, tab3 = st.tabs(["Upload", "Run Analysis", "Review"])


  with tab1:
    with st.expander("Show Help"):
      st.write('')
    
    with st.expander("Upload a CSV file", expanded=True):
      uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], accept_multiple_files=False, help='CSV containing fuel type transactions for S1: Stationary Combustion')
      
      if st.checkbox('Read selected csv files') and uploaded_file:
        data = pd.read_csv(uploaded_file)
        if data is not None:
          df = get_dataframe(data) # cache it
          st.session_state['s1sc_df'] = df

    if st.session_state['s1sc_df'] is not None:
      with st.expander('Show uploaded table'):
        pandas_2_AgGrid(st.session_state['s1sc_df'], theme='balham')

      if 'validated' not in st.session_state:
        st.session_state['validated'] = False
      if st.button('Validate uploaded dataframe'):
        st.session_state['validated_s1sc_df'], st.session_state['validated_s1sc_warnings'] = validate_s1sc_df(st.session_state['s1sc_df'])
        st.session_state['validated'] = True


      if st.session_state['validated']:
        with st.expander('Show validation warnings'):
          for warning in st.session_state['validated_s1sc_warnings']:
            st.warning(warning)

        with st.expander('Validated table', expanded=True):
          pandas_2_AgGrid( st.session_state['validated_s1sc_df'], theme='balham' )

          col1, col2 = st.columns([1,1])
          with col1:
            csv_str = convert_df(st.session_state['validated_s1sc_df'])
            st.download_button('Download validated table as CSV', csv_str, file_name="validated_table.csv", mime="text/csv")
          with col2:
            validation_warnings_str = convert_warnings(st.session_state['validated_s1sc_warnings'])
            st.download_button("Download warnings as TXT", validation_warnings_str, file_name="warnings.txt", mime="text/plain")

  with tab2:
    if 's1sc_df' in st.session_state and st.session_state['s1sc_df'] is not None:
      with st.expander('Show table', expanded=True):
        pandas_2_AgGrid(st.session_state['s1sc_df'], theme='balham', key='abc')

      if 'analyzed' not in st.session_state:
        st.session_state['analyzed'] = False
      if st.button('Analyze uploaded dataframe', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis'):
        st.session_state['analyzed'] = True

        cache = st.session_state['S1SC_Lookup_Cache']
        FCT = FuelCalculatorTool(cache=cache)
        FCT, warning_messages = df_to_FCT(st.session_state['s1sc_df'], fuel_calculator=FCT, cache=cache)
        calculation_df = FCT_to_df(FCT)

        if warning_messages:
          with st.expander('Show analysis warnings'):
            for warning in warning_messages:
              st.warning(warning)

        with st.expander('Show results table'):  
          pandas_2_AgGrid(calculation_df, theme='balham')

        hdata = ['uuid', 'sector', 'fuel_state', 'fuel_type',	'fuel_consumption', 'fuel_unit', 'heating_value',	'fuel_spend',	'currency',	'co2_emission',	'ch4_emission',	'n2o_emission',	'fuel_based_co2e',	'spend_based_co2e',	'most_reliable_co2e',	'recon_score']
        
        figs = {} 
        for c in calculation_df.columns:
          if calculation_df[c].dtype in [np.float64, np.int64]:
            fig = px.histogram(
              calculation_df, 
              x=c, 
              marginal='rug',
              hover_data=hdata,
            ).update_layout(title=c.upper())
            figs[c] = fig 

        for title, fig in figs.items():
          with st.expander(f'Show {title.upper()}'):
            st.plotly_chart(fig, use_container_width=True) 


 






    # with st.expander('Inspect cache'):
    #   st.write(st.session_state['S1SC_Lookup_Cache']._allowed_fuel_types_cache)
      
    #   st.write(st.session_state['S1SC_Lookup_Cache']._emission_factors_cache)
    #   st.write(len(st.session_state['S1SC_Lookup_Cache']._emission_factors_cache))




def validate_s1sc_df(df:pd.DataFrame): 
  """ 
  Validates a pd.DF
  Returns:
    - df
    - List of warnings
  """
  df = df.replace(np.nan, None)
  cache = S1SC_Lookup_Cache()
  warning_messages = []

  expected_columns = [
    'description', 'sector', 'fuel_state', 'fuel_type',
    'fuel_consumption', 'fuel_unit', 'heating_value',
    'fuel_spend', 'currency'
  ]

  # Identify missing and additional columns
  missing_columns = [col for col in expected_columns if col not in df.columns]
  additional_columns = [col for col in df.columns if col not in expected_columns]
    
  # Warn about missing and additional columns
  if missing_columns:
    warning_messages.append(f"Warning: Missing columns {missing_columns}. Please ensure the CSV contains these columns.")
  if additional_columns:
    warning_messages.append(f"Warning: Additional columns {additional_columns}. These columns will be ignored.")

  for index, row in df.iterrows():
    if 'description' in df.columns:
      if len(str(row['description'])) > 255:
        warning_messages.append(f"Warning: Description exceeds 255 characters in row {index}.")

    # validate sector
    if 'sector' in df.columns:
      valid_sectors = [
        'Energy', 'Industrial', 'Construction', 
        # 'Telecommunication', 'Transportation', 'Automobile',
        'Real Estate', 'Consumer Goods', 'Professional Services', None
      ]
      if row['sector'] not in valid_sectors: # sectors is a predefined list of valid sectors
        warning_messages.append(f"Warning: Invalid 'sector' value of '{row['sector']}' in row {index}. Valid sectors: {valid_sectors}. Setting to None.")
        df.loc[index, 'sector'] = None 

    # validate chemical state
    if 'fuel_state' in df.columns:
      valid_states = ['gas', 'liquid', 'solid']
      if row['fuel_state'] not in valid_states:
        warning_messages.append(f"Warning: Invalid 'fuel_state' value of '{row['fuel_state']}' in row {index}. Valid states: {valid_states}. Setting to None.")
        df.loc[index, 'fuel_state'] = None

    # validate fuel type 
    if 'fuel_type' in df.columns:
      try:
        valid_fuel_types = cache.get_allowed_fuel_types(row['fuel_state'])
      except:
        valid_fuel_types = None
      if valid_fuel_types is not None and row['fuel_type'] not in valid_fuel_types:
        warning_messages.append(f"Warning: Invalid 'fuel_type' value of '{row['fuel_type']}' in row {index}. Valid fuel type: {valid_fuel_types}. Setting to None.")
        df.loc[index, 'fuel_type'] = None

    # validate fuel unit
    if 'fuel_unit' in df.columns:
      if row['fuel_state'] == 'gas':
        valid_fuel_unit = ['m3', 'mmBtu']
      elif row['fuel_state'] == 'liquid':
        valid_fuel_unit = ['litre', 'mmBtu']
      elif row['fuel_state'] == 'solid':
        valid_fuel_unit = ['mton', 'kg', 'mmBtu']
      else:
        valid_fuel_unit = None
      if row['fuel_unit'] not in valid_fuel_unit:
        warning_messages.append(f"Warning: Invalid 'fuel_unit' value of '{row['fuel_unit']}' in row {index}. Valid fuel unit for '{row['fuel_state']}': {valid_fuel_unit}.  Setting to None.")
        df.loc[index, 'fuel_unit'] = None

    # validate fuel consumption
    if 'fuel_consumption' in df.columns:
      if row['fuel_consumption'] is not None and row['fuel_consumption'] < 0: 
        warning_messages.append(f"Warning: Invalid 'fuel_consumption' value of '{row['fuel_consumption']}' in row {index}. Must be greater than 0. Setting to None.")
        df.loc[index, 'fuel_consumption'] = None

    # validate heating value
    if 'heating_value' in df.columns:
      valid_heating_value = ['high', 'low', None]
      if row['heating_value'] not in valid_heating_value:
        warning_messages.append(f"Warning: Invalid 'heating_value' value of '{row['heating_value']}' in row {index}. Valid heating value: {valid_heating_value}. Setting to None.")
        df.loc[index, 'heating_value'] = None

    # validate fuel spend
    if 'fuel_spend' in df.columns:
      if row['fuel_spend'] is not None and row['fuel_spend'] < 0:
        warning_messages.append(f"Warning: Invalid 'fuel_spend' value of '{row['fuel_spend']}' in row {index}. Must be greater than 0. Setting to None.")
        df.loc[index, 'fuel_spend'] = None

    # validate currency
    if 'currency' in df.columns:
      valid_currency = ['USD', 'MYR', 'SGD']
      if row['currency'] is not None and row['currency'] not in valid_currency:
        warning_messages.append(f"Warning: Invalid 'currency' value of '{row['currency']}' in row {index}. Supported currency: {valid_currency}. Setting to None.")
        df.loc[index, 'currency'] = None

  return df, warning_messages
    

def df_to_FCT(df, fuel_calculator: FuelCalculatorTool, cache: S1SC_Lookup_Cache):
  df = df.replace(np.nan, None) # To allow Pydantic validation
  warning_messages=[]

  # Create progress bar
  progress_bar = st.progress(0)
  nrows = len(df)

  for index, row in df.iterrows():
    try:
      fuel_data = create_fuel_data(
        cache=cache,
        description=row['description'],
        sector=row['sector'],
        fuel_state=row['fuel_state'],
        fuel_type=row['fuel_type'],
        fuel_consumption=row['fuel_consumption'],
        fuel_unit=row['fuel_unit'],
        heating_value=row['heating_value'],
        fuel_spend=row['fuel_spend'],
        currency=row['currency']
      )
      fuel_calculator.add_fuel_data(fuel_data)
    except Exception as e:
      warning_messages.append(f'Unable to add fuel data for row {index}. {e}')
      pass

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return fuel_calculator, warning_messages

# @st.cache_data
def FCT_to_df(_fuel_calculator_tool:FuelCalculatorTool):
  """ 
  Parameters:
  - _fuel_calculator_tool
  
  Adding the underscore, Streamlit will not to use this argument as part of the 
  cache key. This means that the cached value will not be invalidated 
  if the fuel_calculator_tool state changes.
  """
  data = []
  for emission in _fuel_calculator_tool.calculated_emissions.values():
    fuel_data = emission['fuel'].model_dump()
    calculation_data = emission['calculation_result'].model_dump()
    combined_data = {**fuel_data, **calculation_data}
    data.append(combined_data)
  return pd.DataFrame(data)


def pandas_2_AgGrid(df: pd.DataFrame, theme:str='streamlit', key=None) -> AgGrid:
  cellstyle_jscode = JsCode("""
  function(params){
      if (params.value == null || params.value === '') {
          return {
              'color': 'white',
              'backgroundColor': 'red',
          }
      }
  }
  """)
  custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}} # allows page arrows to be shown

  valid_themes= ['streamlit', 'alpine', 'balham', 'material']
  if theme not in valid_themes:
    raise Exception(f'Theme not in {valid_themes}')

 # AG Grid Options
  gd= GridOptionsBuilder.from_dataframe(df)
  gd.configure_columns(df, cellStyle=cellstyle_jscode)
  # gd.configure_default_column(floatingFilter=True, selectable=False)
  gd.configure_pagination(enabled=True)
  
  grid_options = gd.build()
  grid_response = AgGrid(
    df, 
    gridOptions=grid_options,
    custom_css=custom_css,
    height=600, 
    theme=theme,
    reload_data=True,
    allow_unsafe_jscode=True,
    key=key,
  )
  return grid_response['data']

@st.cache_data
def convert_df(df):
  return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_warnings(warnings: List):
  warnings_str = "\n".join(warnings)
  return warnings_str
