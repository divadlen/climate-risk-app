import streamlit as st

import numpy as np
import pandas as pd

import plotly.express as px

from utils.s1mc_VehicleData import create_vehicle_data, S1MC_Lookup_Cache, VehicleData, S1MC_CalculatorTool
from utils.utility import get_dataframe, convert_df, convert_warnings, find_closest_category
from utils.display_utility import show_example_form, pandas_2_AgGrid


def s1mc_Page():
  if 'S1MC_Lookup_Cache' not in st.session_state:
    st.session_state['S1MC_Lookup_Cache'] = S1MC_Lookup_Cache() 
  if 's1mc_df' not in st.session_state: #
    st.session_state['s1mc_df'] = None
  if 'validated_s1mc_df' not in st.session_state:
    st.session_state['validated_s1mc_df'] = None
    st.session_state['validated_s1mc_warnings'] = []

  st.title('Mobile Combustion')
  tab1, tab2, tab3 = st.tabs(["Upload", "Run Analysis", "Review"]) 


  with tab1:
    footer_md = """*(Highlighted columns with <Blank> are optional. Blue column indicates recommended default values)*"""

    with st.expander("Show help", expanded=True):
      st.markdown(help_md)
    show_example_form(VehicleData, title='Show example form (S1: Mobile Combustion)', button_text='Get example form', filename='s1-mobile_combustion-example.csv', markdown=footer_md)

    with st.expander("Upload a CSV file", expanded=True):
      uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], accept_multiple_files=False, help='CSV containing vehicle usage data for S1: Mobile Combustion')
      
      if st.checkbox('Read selected csv files', key='s1mc_check') and uploaded_file:
        data = pd.read_csv(uploaded_file)
        if data is not None:
          df = get_dataframe(data) 
          st.session_state['s1mc_df'] = df

    if st.session_state['s1mc_df'] is not None:
      with st.expander('Show uploaded table'):
        pandas_2_AgGrid(st.session_state['s1mc_df'], theme='balham')

      if 'validated_s1mc' not in st.session_state:
        st.session_state['validated_s1mc'] = False
      if st.button('Validate uploaded dataframe'):
        st.session_state['validated_s1mc_df'], st.session_state['validated_s1mc_warnings'] = validate_s1mc_df(st.session_state['s1mc_df'])
        st.session_state['validated_s1mc'] = True


      if st.session_state['validated_s1mc']:
        with st.expander('Show validation warnings'):
          for warning in st.session_state['validated_s1mc_warnings']:
            st.warning(warning)

        with st.expander('Validated table', expanded=True):
          pandas_2_AgGrid( st.session_state['validated_s1mc_df'], theme='balham' )

          col1, col2 = st.columns([1,1])
          with col1:
            csv_str = convert_df(st.session_state['validated_s1mc_df'])
            st.download_button('Download validated table as CSV', csv_str, file_name="validated_table.csv", mime="text/csv")
          with col2:
            validation_warnings_str = convert_warnings(st.session_state['validated_s1mc_warnings'])
            st.download_button("Download warnings as TXT", validation_warnings_str, file_name="warnings.txt", mime="text/plain")


  with tab2:
    with st.expander('Show help'):
      st.markdown(analysis_md)

    if 's1mc_df' not in st.session_state or st.session_state['s1mc_df'] is None:
      st.info('Please upload a table at "Upload" tab to continue')

    if 's1mc_df' in st.session_state and st.session_state['s1mc_df'] is not None:
      with st.expander('Show table', expanded=True):
        pandas_2_AgGrid(st.session_state['s1mc_df'], theme='balham', key='s1mc_df_tab2')

      if 'analyzed_s1mc' not in st.session_state:
        st.session_state['analyzed_s1mc'] = False
      if st.button('Analyze uploaded dataframe', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis'):
        st.session_state['analyzed_s1mc'] = True

        cache = st.session_state['S1MC_Lookup_Cache']
        calc = S1MC_CalculatorTool(cache=cache)

        calc, warning_messages = df_2_calculator(st.session_state['s1mc_df'], calculator=calc, cache=cache)
        calculation_df = calculator_2_df(calc)

        if warning_messages:
          with st.expander('Show analysis warnings'):
            for warning in warning_messages:
              st.warning(warning)

        with st.expander('Show results table'):  
          pandas_2_AgGrid(calculation_df, theme='balham')

        # figs = {} 
        # for c in calculation_df.columns:
        #   if calculation_df[c].dtype in [np.float64, np.int64]:
        #     fig = px.histogram(
        #       calculation_df, 
        #       x=c, 
        #       marginal='rug',
        #       hover_data=calculation_df.columns,
        #     ).update_layout(title=c.upper())
        #     figs[c] = fig 

        # for title, fig in figs.items():
        #   with st.expander(f'Show {title.upper()}'):
        #     st.plotly_chart(fig, use_container_width=True) 







def validate_s1mc_df(df:pd.DataFrame): 
  """ 
  Validates a pd.DF
  Returns:
    - df
    - List of warnings
  """
  df = df.replace(np.nan, None)
  df = df.replace('<Blank>', None)
  cache = S1MC_Lookup_Cache()
  warning_messages = []

  expected_columns = [
    'description', 'vehicle_type', 'distance', 'distance_unit',
    'fuel_state', 'fuel_type', 'fuel_consumption', 'fuel_unit',
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

    # validate vehicle type
    if 'vehicle_type' in df.columns:
      valid_vehicle_types = cache.get_allowed_vehicles()

      if row['vehicle_type'] not in valid_vehicle_types:
        corrected_vehicle = find_closest_category(row['vehicle_type'], valid_vehicle_types)
        
        if corrected_vehicle is not None: 
          warning_messages.append(f"Warning: 'vehicle_type' value of '{row['vehicle_type']}' in row {idx} is corrected to '{corrected_vehicle}'. Accepted values: {valid_vehicle_types}.")
          df.loc[index, 'vehicle_type'] = corrected_vehicle 
        else:
          warning_messages.append(f"Warning: Invalid 'vehicle_type' value of '{row['vehicle_type']}' in row {idx}. Accepted values in: {valid_vehicle_types}. Setting to None.")
          df.loc[index, 'vehicle_type'] = None 

    # validate fuel type 
    if 'fuel_type' in df.columns:
      try:
        valid_fuel_types = cache.get_allowed_fuel_types(row['vehicle_type'])
      except:
        valid_fuel_types = None
      
      if valid_fuel_types is not None and row['fuel_type'] not in valid_fuel_types:
        corrected_fuel_type = find_closest_category(row['fuel_type'], valid_fuel_types)

        if corrected_fuel_type is not None:
          warning_messages.append(f"Warning: 'fuel_type' value of '{row['fuel_type']}' in row {idx} is corrected to '{corrected_fuel_type}'. Accepted fuel type for '{row['vehicle_type']}': {valid_fuel_types}.")
          df.loc[index, 'fuel_type'] = corrected_fuel_type
        else:
          warning_messages.append(f"Warning: Invalid 'fuel_type' value of '{row['fuel_type']}' in row {idx}. Accepted fuel type for '{row['vehicle_type']}': {valid_fuel_types}. Setting to None.")
          df.loc[index, 'fuel_type'] = None 

    # validate fuel unit
    if 'fuel_unit' and 'fuel_state' in df.columns:
      if row['fuel_state'] == 'gas':
        valid_fuel_unit = ['m3', 'mmBtu']
      elif row['fuel_state'] == 'liquid':
        valid_fuel_unit = ['litre', 'mmBtu']
      elif row['fuel_state'] == 'solid':
        valid_fuel_unit = ['mton', 'kg', 'mmBtu']
      else:
        valid_fuel_unit = None
      if row['fuel_unit'] not in valid_fuel_unit:
        warning_messages.append(f"Warning: Invalid 'fuel_unit' value of '{row['fuel_unit']}' in row {idx}. Valid fuel unit for '{row['fuel_state']}': {valid_fuel_unit}.  Setting to None.")
        df.loc[index, 'fuel_unit'] = None

    # validate fuel consumption
    if 'fuel_consumption' in df.columns:
      if row['fuel_consumption'] is not None and row['fuel_consumption'] < 0: 
        warning_messages.append(f"Warning: Invalid 'fuel_consumption' value of '{row['fuel_consumption']}' in row {idx}. Must be greater than 0. Setting to None.")
        df.loc[index, 'fuel_consumption'] = None

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return df, warning_messages


def df_2_calculator(df, calculator: S1MC_CalculatorTool, cache: S1MC_Lookup_Cache):
  df = df.replace(np.nan, None) # To allow Pydantic validation
  df = df.replace('<Blank>', None)
  warning_messages=[]

  # Create progress bar
  progress_bar = st.progress(0)
  nrows = len(df)

  for index, row in df.iterrows():
    try:
      data = create_vehicle_data(
        cache=cache,
        description=row['description'],
        vehicle_type=row['vehicle_type'],
        distance=row['distance'],
        distance_unit=row['distance_unit'],
        fuel_type=row['fuel_type'],
        fuel_consumption=row['fuel_consumption'],
        fuel_unit=row['fuel_unit'],
      )
      calculator.add_vehicle_data(data)
        
    except Exception as e:
      warning_messages.append(f'Unable to add data for row {index+1}. {str(e)}')
      pass

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return calculator, warning_messages


def calculator_2_df(calculator: S1MC_CalculatorTool):
  data = []
  for emission in calculator.calculated_emissions.values():
    fuel_data = emission['vehicle'].model_dump()
    calculation_data = emission['calculated_emissions'].model_dump()
    combined_data = {**fuel_data, **calculation_data}
    data.append(combined_data)
  return pd.DataFrame(data)


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
