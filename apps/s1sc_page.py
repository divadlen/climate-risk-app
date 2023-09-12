import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
import json
import logging
from typing import List
from supabase import create_client

import plotly.express as px

from utils.s1sc_FuelData import create_fuel_data, S1SC_Lookup_Cache, FuelData, FuelCalculatorTool
from utils.utility import get_dataframe, convert_df, convert_warnings, convert_BaseModel, find_closest_category

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
    with st.expander("Show help"):
      st.markdown(help_md)

      csv_str = convert_BaseModel(FuelData)
      st.download_button(
        label='Download empty Scope 1: Stationary Combustion form',
        data=csv_str,
        file_name='scope-1-stationary-combustion-form.csv',
        mime='text/csv',
      )
    
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

      if 'validated_s1sc' not in st.session_state:
        st.session_state['validated_s1sc'] = False
      if st.button('Validate uploaded dataframe'):
        st.session_state['validated_s1sc_df'], st.session_state['validated_s1sc_warnings'] = validate_s1sc_df(st.session_state['s1sc_df'])
        st.session_state['validated_s1sc'] = True


      if st.session_state['validated_s1sc']:
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
    with st.expander('Show help'):
      st.markdown(analysis_md)

    if 's1sc_df' not in st.session_state or st.session_state['s1sc_df'] is None:
      st.info('Please upload a table at "Upload" tab to continue')

    if 's1sc_df' in st.session_state and st.session_state['s1sc_df'] is not None:
      with st.expander('Show table', expanded=True):
        pandas_2_AgGrid(st.session_state['s1sc_df'], theme='balham', key='s1sc_df_tab2')

      if 'analyzed_s1sc' not in st.session_state:
        st.session_state['analyzed_s1sc'] = False
      if st.button('Analyze uploaded dataframe', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis'):
        st.session_state['analyzed_s1sc'] = True

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

        # hdata = ['uuid', 'sector', 'fuel_state', 'fuel_type',	'fuel_consumption', 'fuel_unit', 'heating_value',	'fuel_spend',	'currency',	'co2_emission',	'ch4_emission',	'n2o_emission',	'fuel_based_co2e',	'spend_based_co2e',	'most_reliable_co2e',	'recon_score']
        # figs = {} 
        # for c in calculation_df.columns:
        #   if calculation_df[c].dtype in [np.float64, np.int64]:
        #     fig = px.histogram(
        #       calculation_df, 
        #       x=c, 
        #       marginal='rug',
        #       hover_data=hdata,
        #     ).update_layout(title=c.upper())
        #     figs[c] = fig 

        # for title, fig in figs.items():
        #   with st.expander(f'Show {title.upper()}'):
        #     st.plotly_chart(fig, use_container_width=True) 



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

  progress_bar = st.progress(0)
  nrows = len(df)
  for index, row in df.iterrows():
    idx = index + 1

    if 'description' in df.columns:
      if len(str(row['description'])) > 1200:
        warning_messages.append(f"Warning: Description exceeds 1200 characters in row {idx}.")

    # validate sector
    if 'sector' in df.columns:
      sector = row['sector']
      valid_sectors = [
        'Energy', 'Industrial', 'Construction', 
        'Telecommunication', 'Transportation', 'Automobile',
        'Real Estate', 'Consumer Goods', 'Professional Services', None
      ]
      if sector not in valid_sectors:
        corrected_sector = find_closest_category(sector, valid_sectors)

        if corrected_sector is not None: 
          warning_messages.append(f"UPDATE: 'sector' value of '{sector}' in row {idx} is corrected to '{corrected_sector}'. Accepted values: {valid_sectors}.")
          df.loc[index, 'sector'] = corrected_sector
        else:
          warning_messages.append(f"Warning: Invalid 'sector' value of '{sector}' in row {idx}. Valid fuel type: {valid_sectors}. Setting to None.")
          df.loc[index, 'fuel_sector'] = None

    # validate chemical state
    if 'fuel_state' in df.columns:
      valid_states = ['gas', 'liquid', 'solid']
      if row['fuel_state'] not in valid_states:
        warning_messages.append(f"Warning: Invalid 'fuel_state' value of '{row['fuel_state']}' in row {idx}. Valid states: {valid_states}. Setting to None.")
        df.loc[index, 'fuel_state'] = None

    # validate fuel type 
    if 'fuel_type' in df.columns:
      fuel_type = row['fuel_type']
      try:
        valid_fuel_types = cache.get_allowed_fuel_types(row['fuel_state'])
      except:
        valid_fuel_types = None

      if valid_fuel_types is not None and fuel_type not in valid_fuel_types:
        corrected_fuel_type = find_closest_category(fuel_type, valid_fuel_types)

        if corrected_fuel_type is not None: 
          warning_messages.append(f"UPDATE: 'fuel_type' value of '{fuel_type}' in row {idx} is corrected to '{corrected_fuel_type}'. Accepted values for state '{row['fuel_state']}': {valid_fuel_types}.")
          df.loc[index, 'fuel_type'] = corrected_fuel_type
        else:
          warning_messages.append(f"Warning: Invalid 'fuel_type' value of '{fuel_type}' in row {idx}. Valid fuel type: {valid_fuel_types}. Setting to None.")
          df.loc[index, 'fuel_type'] = None

    # validate fuel unit
    if 'fuel_unit' in df.columns:
      fuel_unit = row['fuel_unit']
      if row['fuel_state'] == 'gas':
        valid_fuel_unit = ['m3', 'mmBtu']
      elif row['fuel_state'] == 'liquid':
        valid_fuel_unit = ['litre', 'mmBtu']
      elif row['fuel_state'] == 'solid':
        valid_fuel_unit = ['mton', 'kg', 'mmBtu']
      else:
        valid_fuel_unit = [None]

      if fuel_unit not in valid_fuel_unit:
        corrected_fuel_unit = find_closest_category(fuel_unit, valid_fuel_unit)

        if corrected_fuel_unit is not None:
          warning_messages.append(f"UPDATE: 'fuel_unit' value of '{fuel_unit}' in row {idx} is corrected to '{corrected_fuel_unit}'. Accepted values: {valid_fuel_unit}.")
          df.loc[index, 'fuel_unit'] = corrected_fuel_unit
        else:
          warning_messages.append(f"Warning: Invalid 'fuel_unit' value of '{fuel_unit}' in row {idx}. Valid fuel unit for '{row['fuel_state']}': {valid_fuel_unit}.  Setting to None.")
          df.loc[index, 'fuel_unit'] = None

    # validate fuel consumption
    if 'fuel_consumption' in df.columns:
      if row['fuel_consumption'] is not None and row['fuel_consumption'] < 0: 
        warning_messages.append(f"Warning: Invalid 'fuel_consumption' value of '{row['fuel_consumption']}' in row {idx}. Must be greater than 0. Setting to None.")
        df.loc[index, 'fuel_consumption'] = None

    # validate heating value
    if 'heating_value' in df.columns:
      valid_heating_value = ['high', 'low', None]
      if row['heating_value'] not in valid_heating_value:
        warning_messages.append(f"Warning: Invalid 'heating_value' value of '{row['heating_value']}' in row {idx}. Valid heating value: {valid_heating_value}. Setting to None.")
        df.loc[index, 'heating_value'] = None

    # validate fuel spend
    if 'fuel_spend' in df.columns:
      if row['fuel_spend'] is not None and row['fuel_spend'] < 0:
        warning_messages.append(f"Warning: Invalid 'fuel_spend' value of '{row['fuel_spend']}' in row {idx}. Must be greater than 0. Setting to None.")
        df.loc[index, 'fuel_spend'] = None

    # validate currency
    if 'currency' in df.columns:
      valid_currency = ['USD', 'MYR', 'SGD']
      if row['currency'] is not None and row['currency'] not in valid_currency:
        warning_messages.append(f"Warning: Invalid 'currency' value of '{row['currency']}' in row {idx}. Supported currency: {valid_currency}. Setting to None.")
        df.loc[index, 'currency'] = None

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

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
      warning_messages.append(f'Unable to add fuel data for row {index+1}. {e}')
      pass

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return fuel_calculator, warning_messages


def FCT_to_df(fuel_calculator_tool:FuelCalculatorTool):
  data = []
  for emission in fuel_calculator_tool.calculated_emissions.values():
    fuel_data = emission['fuel'].model_dump()
    calculation_data = emission['calculated_emissions'].model_dump()
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
  
  # check if column cell is in json or dict, then transform column to json literal string 
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, dict)).any():
      df[col] = df[col].apply(json.dumps)

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


## Markdowns
help_md = """
- ##### Uploading CSV file
  - Drag and drop file into the widget. Supported files (csv). If you are not sure what files to upload, **download empty form at the end of help**. 
  - Click "Read selected csv files". A table preview will show up for your uploaded data. 
  - A red cell indicates an empty field. This is only for visual purposes. Only missing values that affect the analysis will be raised during the "Warning" section. 
  
- ##### Validating uploaded CSV file
  - Clicking button "Validate uploaded dataframe" is optional but recommended. 
  - Validation will pick up corrected spellings, updated fields, and warn about missing or incorrect values.
    - Warning: Validation is not perfect! Sometimes it may incorrectly update values! EG: Liquified Petroleum Gas >> Petroleum (when it should be LPG). 
  - "Show validation warnings" or download its TXT file to perform audits on which row to update.
  - You may also choose to download the validated table and make modifications from there. Don't forget to reupload the modified table to the app.                   
"""

analysis_md = """
- ##### Analyzing uploaded data
  - You are required to click "Analyze uploaded dataframe" to commit the analyzed result to the final dashboard. 
  - Will use uploaded data and not validated data to analyze. If you have used the validation feature, remember to reupload your modified data.
  - "Show results table" to display the raw output of the model
"""
