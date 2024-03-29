import streamlit as st
from streamlit import session_state as state
import streamlit_antd_components as sac
from streamlit_extras.metric_cards import style_metric_cards

import numpy as np
import pandas as pd

from functools import partial
import plotly.express as px
import plotly.graph_objects as go

from utils.s2ie_Misc.s2_models import S2_PurchasedPower
from utils.s2ie_Misc.s2_calculators import S2_Calculator
from utils.s2ie_Misc.s2_creators import create_s2pp_data
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache

from utils.model_inferencer import ModelInferencer
from utils.utility import get_dataframe, format_metric
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.md_utility import markdown_insert_images
from utils.model_df_utility import calculator_to_df, df_to_calculator, calculators_2_df
from utils.geolocator import GeoLocator


def s2ie_Page():
  if 'geolocator' not in state:
    state['geolocator'] = GeoLocator() # constructors cant use state.get() method
  if 'S2IE_Lookup_Cache' not in state:
    state['S2IE_Lookup_Cache'] = S3_Lookup_Cache()

  user_level = state.get("user_level", 1)
  state['s2ie_original_dfs'] = state.get('s2ie_original_dfs', {})
  state['s2ie_result_dfs'] = state.get('s2ie_result_dfs', {})
  state['s2ie_warnings'] = state.get('s2ie_warnings', {})
  state['s2ie_calc_results'] = state.get('s2ie_calc_results', {})

  st.title('Scope 2: Indirect Emissions')
  tab1, tab2, tab3 = st.tabs(['Get Forms/Guidelines', 'Submit & Review', 'Analysis'])

  with tab1:
    st.subheader('User Guide')

    with st.expander('Show help', expanded=True):
      download_desc = 'Click on the links in Table of Contents to redirect you to the recommended tables to fill. Download the example forms. Each transaction counts as a row.'
      fill_desc = 'Each form is represented as CSV, each row is one transaction. Example: in "Mobile Combustion" file, each vehicle/machine counts as one row. Details at "More help" and "Visual help"'
      upload_desc = 'In "Submit & Review" tab, drag and drop your csv files in the upload window.'
      validate_desc = 'In "Submit & Review" tab, go to "Analyze uploads" to verify your uploaded files. From there, our AI validator will simulate the results of your submitted files.'

      sac.steps(
        items=[
          sac.StepsItem(title='Download relevant forms', subtitle='', description=download_desc),
          sac.StepsItem(title='Fill relevant forms', subtitle='', description=fill_desc),
          sac.StepsItem(title='Upload relevant forms', subtitle='', description=upload_desc),
          sac.StepsItem(title='Validate & submit forms', subtitle='', description=validate_desc),
        ], 
        format_func='title',
        direction='vertical',
      )

    with st.expander('Visual help'):
      with open("resources/mds/s2ie-general-guide.md", "r") as gmd:
        readme = gmd.read()
      readme = markdown_insert_images(readme)
      st.markdown(readme, unsafe_allow_html=True) 
    st.divider()

    st.subheader("Purchased Power Source", anchor='S2_PurchasedPower')
    show_example_form(S2_PurchasedPower, key='s2ppd', title='Show example form (S2-C0: Purchased Power)', button_text='Get example form', filename='s2-c0-purchased-power-example.csv', markdown=footer_md, expanded=True)


  with tab2:
    t1, t2 = st.tabs(['Upload/Validate', 'Analyze uploads'])

    with t1:        
      st.info('*(For best results, upload only csv files containing matching fields from examples and keep edits to recommended default fields to minimum)*')

      if user_level >=10:
        st.error('File upload feature not available for demo accounts')
      else:
        with st.form('Upload CSV files'):
          uploaded_file = st.file_uploader("Upload a CSV file (accepts only 1 file)", type=["csv"], accept_multiple_files=False, help='CSV containing purchased power data for S2: Indirect Emissions')

          c1,c2 = st.columns([1,1])
          with c1:
            submit_button = st.form_submit_button('Upload')

          if submit_button and uploaded_file:
            s2_inits = {
              's2ie_warnings': {},
              's2ie_invalid_indices': {},
              's2ie_original_dfs': {},
              's2ie_result_dfs': {},
              's2ie_calc_results': {},
            }

            # Loop to initialize variables in state if not present
            for var_name, default_value in s2_inits.items(): 
              state[var_name] = default_value # reset everything if button is clicked
          
            # Inferencer and df inits
            modinf = ModelInferencer()
            cache = state['S2IE_Lookup_Cache']
            gl = state['geolocator']
            s2_models = ['S2_PurchasedPower']

            data = pd.read_csv(uploaded_file)
            if data is not None:
              df = get_dataframe(data)
              inferred_model = modinf.infer_model_from_df(df=df)
              
              if inferred_model is None:
                st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches. Please make sure you are submitting a file that closely resemble the examples.')
                st.stop()
              
              model_name = inferred_model['model']
              Model = modinf.available_models[model_name]

              # Store the filename with the model name
              if 'model_filenames' not in state:
                state['model_filenames'] = {}
              state['model_filenames'][model_name] = uploaded_file.name

              if model_name not in s2_models:
                st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches against Scope 2 forms. Skipping...')
                st.stop()
              
              CREATOR_FUNCTIONS = {
                'S2_PurchasedPower': partial( create_s2pp_data, Model=Model, cache=cache, geolocator=gl ),
              }
              calc = S2_Calculator(cache=cache)
              creator = CREATOR_FUNCTIONS[model_name]

              try:
                calc, warning_list, invalid_indices = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False, return_invalid_indices=True)
                result_df = calculator_to_df(calc)

                if len(warning_list) > 0:
                  state['s2ie_warnings'][model_name] = warning_list
                  state['s2ie_invalid_indices'][model_name] = invalid_indices
                state['s2ie_original_dfs'][model_name] = df
                state['s2ie_result_dfs'][model_name] = result_df
                state['s2ie_calc_results'][model_name] = calc
              
              except Exception as e:
                raise


    with t2:
      with st.expander('Show help', expanded=False):
        with open("resources/mds/s1sc-validation-guide-1.md", "r") as gmd:
          readme = gmd.read()
          readme = markdown_insert_images(readme) 
          st.markdown(readme, unsafe_allow_html=True) 

      if 's2ie_original_dfs' not in state or state['s2ie_original_dfs'] in [{}]:
        st.info('Please upload at least one valid table at "Upload/Validate" tab to continue')

      if 's2ie_original_dfs' in state and state['s2ie_original_dfs'] not in [{}]:
        with st.expander('Show uploaded table', expanded=True):
          for name, df in state['s2ie_original_dfs'].items():
            pandas_2_AgGrid(df.head(20), theme='balham', height=300, key=f's2ie_og_{name}_aggrid')

      if 'analyzed_s2ie' not in state:
        st.session_state['analyzed_s2ie'] = False
      
      analyze_button = st.button('Validate uploaded dataframes', help='Attempts to return calculation results for each row for table.')
      if analyze_button and state['s2ie_original_dfs'] not in [{}]:
        state['analyzed_s2ie'] = True   
        st.success('Uploaded Scope 2 data tables analyzed!')
        
        st.divider()
        st.subheader('Validation Results')

        if all(key in state for key in ['s2ie_warnings', 's2ie_original_dfs']) and state.get('analyzed_s2ie', True):
          with st.expander('Show warnings'):
            for name, warnings in state['s2ie_warnings'].items():
              for warn in warnings:
                st.warning(f'{name}: {warn}')

            for name, df in state['s2ie_original_dfs'].items():
              df = df.replace('<Blank>', None)
              df = df.replace('<To fill>', None)
              df = df.replace(np.nan, None)
              pandas_2_AgGrid(
                df, theme='balham', height=300, key=f's2ie_warn_{name}_aggrid', 
                highlighted_rows=state['s2ie_invalid_indices'].get(name, [])  # Returns an empty list if 'name' is not in the dictionary
              )
          
          for name, df in state['s2ie_result_dfs'].items():
            with st.expander(f'Show table for analyzed **{name}**'):
              pandas_2_AgGrid(df, theme='balham', height=300, key=f's1de_{name}_aggrid')
      

    with tab3:
      st.subheader('Executive Insights')
      if 's2ie_calc_results' not in st.session_state or st.session_state['s2ie_calc_results'] == {}:
        st.error('Nothing to display here. Have you uploaded or analyzed your uploaded files?')

      if 's2ie_calc_results' in st.session_state and st.session_state['s2ie_calc_results'] != {}:
        # Check if warnings are discovered
        if len(state['s2ie_warnings'].items()) > 0:
            st.error('Invalid data table values found. Please refer to error logs in "Show warnings". Directory: "Submit & Review" >> "Analyze uploads"')
            st.stop()

        res_df = st.session_state['s2ie_calc_results'] # key: Model name, val: Calculator
        res_df = calculators_2_df(res_df) # convert each k/v to df
        
        emissionOverviewPart(df=res_df)

        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')
        st.write('')



def emissionOverviewPart(df):      
    # Global styling
    style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

    total_s2 = df[df['scope'] == 2]['emission_result'].sum()
    st.metric(label="Scope 2 Emissions", value=format_metric(total_s2))
    st.divider()

    st.subheader('Top contributors')

    # Allowed columns for groupby selection
    potential_columns = ['country', 'branch', 'department', 'city', 'state']

    # Filter out the columns that actually exist in the DataFrame
    available_columns = [col for col in potential_columns if col in df.columns]

    c1, c2 = st.columns([1, 3])
    with c1:
      selected_group = st.selectbox('Select group', options=available_columns)

    # Group DataFrame by selected option, sum, then sort
    grouped_df = df.groupby(selected_group)['emission_result'].sum().reset_index()
    sorted_df = grouped_df.sort_values('emission_result', ascending=False)
    sorted_df['delta'] = round( sorted_df['emission_result'].pct_change(-1).fillna(0) * 100, 2)

    # Limit to top 10 and combine the rest as 'Others'
    top_10_df = sorted_df.head(10)
    others_sum = sorted_df.iloc[10:]['emission_result'].sum()
    others_delta = sorted_df.iloc[9]['emission_result'] - others_sum if len(sorted_df) > 10 else 0
    others_df = pd.DataFrame({selected_group: ['Others'], 'emission_result': [others_sum], 'delta': [others_delta]})
    top_10_df = pd.concat([top_10_df, others_df], ignore_index=True)

    with c1:
      for index, row in top_10_df.head(5).iterrows():
        st.metric(label=f"{row[selected_group]} Emissions", value=format_metric(row['emission_result']), delta=f"{row['delta']}%")

    # Vertical Bar Chart with Cumulative Sum
    total_emission = top_10_df['emission_result'].sum()
    top_10_df['cum_sum'] = top_10_df['emission_result'].cumsum()
    top_10_df['cum_sum_percent'] = (top_10_df['cum_sum'] / total_emission) * 100

    fig = go.Figure()
    for index, row in top_10_df.iterrows():
      fig.add_trace(go.Bar(
        x=[row[selected_group]],  # x should be a list or array
        y=[row['emission_result']],  # y should also be a list or array
        name=str(row[selected_group]),
        yaxis='y1',
        hovertemplate=f"%{{value:.2f}} kg"
      ))

    # Cumulative Sum Line
    fig.add_trace(go.Scatter(
      x=top_10_df[selected_group],
      y=top_10_df['cum_sum_percent'],
      mode='lines+markers',
      name='Cumulative Sum (%)',
      yaxis='y2',
      hovertemplate ='%{y:.2f} %',
    ))

    # Update layout
    fig.update_layout(
      title='',
      xaxis_title=f'<b>{selected_group}</b>',
      yaxis=dict(title='<b>Emission Result</b>'),
      yaxis2=dict(
        title='<b>Cumulative Sum (%)</b>',
        overlaying='y',
        side='right',
        range=[0, 100]
      ),
      height=800,
      template='google',
      legend=dict(
        orientation='h', title=None,
        x=0.5, y=1, xanchor='center', yanchor='bottom'
      ),
      showlegend=True,
      hovermode="x",
      hoverlabel=dict(font_size=18),
    )
    
    with c2:
      st.plotly_chart(fig, use_container_width=True)




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

footer_md = """*(<Blank> and <To fill> are optional. <To fill> indicates optional fields that can affect calculations. Blue indicates REQUIRED fields with recommended default values. Orange indicates REQUIRED fields.)*"""
