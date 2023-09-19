import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
from functools import partial
import json
import logging
from typing import List
from supabase import create_client

import plotly.express as px

from utils.globals import SECTOR_TO_CATEGORY_IDX, IDX_TO_CATEGORY_NAME, ColorDiscrete
from utils.utility import get_dataframe, convert_df, convert_warnings, create_line_simulation
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.model_df_utility import df_to_calculator, calculator_to_df
from utils.md_utility import markdown_insert_images
from utils.model_inferencer import ModelInferencer

from utils.s3vc_Misc.s3_models import *
from utils.s3vc_Misc.s3c15_models import *
from utils.s3vc_Misc.s3c15_calculators import S3C15_Calculator, create_s3c15_data
from utils.charting import initialize_plotly_themes, make_bar_chart, make_donut_chart, make_grouped_line_chart, make_sankey_chart


def s3vc_Page(): 
  # inits already done in 'app_config()'
  initialize_plotly_themes()

  st.title('Scope 3: Value Chain')  
  if not st.session_state.get('s3_settings'):
    with st.form(key='scope_3_config'):
      valid_sectors = list(SECTOR_TO_CATEGORY_IDX.keys())
      sector = st.selectbox('Select Sector', options=valid_sectors)
      
      if st.form_submit_button('Confirm settings'):
        with st.spinner():
          st.session_state["s3_settings"] = True
          st.session_state['s3_sector'] = sector
          st.experimental_rerun()


  if 's3_settings' in st.session_state and st.session_state['s3_settings'] == True:
    tab1, tab2, tab3, tab4 = st.tabs(['Settings', 'Get Forms/Guidelines', 'Submit & Review', 'Analysis'])
    applicable_indices = SECTOR_TO_CATEGORY_IDX.get(st.session_state['s3_sector'], None)
    
    try:
      sorted_applicable_indices = sorted(list(set(applicable_indices)))
      applicable_bools = [i in sorted_applicable_indices for i in range(1, 16)]        
    except:
      sorted_applicable_indices = None
      applicable_bools = [False] * 15

    with tab1:
      with st.form(key='scope_3_reset'):
        st.success(f"Current sector: {st.session_state['s3_sector']}")
        st.info(f'Highighted rows indicate the *recommended* scopes to be covered by industry. Navigate to **Get Forms/Guidelines** or **Submit & Review** to get started!')

        df = pd.DataFrame({
          'Category': [IDX_TO_CATEGORY_NAME[i] for i in range(1,16)],
          'Applicable': applicable_bools
        })

        cellstyle_jscode = JsCode("""
        function(params){
            if (params.data.Applicable === true) {
                return {
                    'backgroundColor': 'lightblue',
                }
            } else {
                return {
                    'color': 'black',
                    'backgroundColor': 'white',
                }
            }
        }
        """)
        pandas_2_AgGrid(df, cellstyle_jscode=cellstyle_jscode, height=None, pagination=None)

        if st.form_submit_button('Reset settings'):
          del st.session_state['s3_settings']
          st.experimental_rerun() 


    with tab2:
      footer_md = """*(Highlighted columns with <Blank> are optional. Blue column indicates recommended default values)*"""
      
      st.subheader('User Guide')
      with st.expander('Show help', expanded=True):
        st.markdown(general_guide_md)

      with st.expander('Visual help'):
        with open("resources/mds/s3vc_general_guide.md", "r") as gmd:
          readme = gmd.read()
        readme = markdown_insert_images(readme)
        st.markdown(readme, unsafe_allow_html=True) 

      st.subheader('Table of contents', anchor='s3-toc')
      with st.expander('Show table of contents', expanded=True):
        st.markdown(table_of_contents_md)
      st.divider()

      # REMEMBER TO CHANGE THE BASE ASSETS
      t1, t2, t3, t4 = st.tabs(['Category 1-5', 'Category 6-10', 'Category 11-14', 'Category 15: Investments'])
      with t1:
        st.subheader("Category 1 : Purchased goods & services", anchor='S3C1_PurchasedGoods')
        show_example_form(S3_BaseAsset, key='c1', title='Show example form (S3-C1: Purchased goods & services)', button_text='Get example form', filename='s3-c1-purchased_goods-example.csv', markdown=footer_md)

        st.subheader("Category 2 : Capital goods", anchor='S3C2_CapitalGoods')
        show_example_form(S3_BaseAsset, key='c2', title='Show example form (S3-C2: Capital Goods)', button_text='Get example form', filename='s3-c2-capital_goods-example.csv', markdown=footer_md)

        st.subheader("Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)", anchor='S3C3_EnergyRelated')
        show_example_form(S3_BaseAsset, key='c3', title='Show example form (S3-C3: Energy-related activities)', button_text='Get example form', filename='s3-c3-energy_related-example.csv', markdown=footer_md)

        st.subheader("Category 4 : Upstream transportation & distribution", anchor='S3C4_UpstreamTransport')
        show_example_form(S3_BaseAsset, key='c4', title='Show example form (S3-C4: Upstream transportation and distribution)', button_text='Get example form', filename='s3-c4-upstream_transport-example.csv', markdown=footer_md)
        
        st.subheader("Category 5 : Waste generated in operations", anchor='S3C5_WasteGenerated')
        show_example_form(S3_BaseAsset, key='c5', title='Show example form (S3-C5: Waste generated in operations)', button_text='Get example form', filename='s3-c5-waste_generated-example.csv', markdown=footer_md)

      
      with t2:
        st.subheader("Category 6 : Business and air travel", anchor='S3C6_BusinessTravel')
        show_example_form(S3_BaseAsset, key='c6', title='Show example form (S3-C6: Business and air travel)', button_text='Get example form', filename='s3-c6-business_travel-example.csv', markdown=footer_md)

        st.subheader("Category 7 : Employee commuting", anchor='S3C7_EmployeeCommute')
        show_example_form(S3_BaseAsset, key='c7', title='Show example form (S3-C7: Employee commuting)', button_text='Get example form', filename='s3-c7-employee_commute-example.csv', markdown=footer_md)

        st.subheader("Category 8 : Upstream leased assets", anchor='S3C8_UpstreamLeased')
        show_example_form(S3_BaseAsset, key='c8', title='Show example form (S3-C8: Upstream leased assets)', button_text='Get example form', filename='s3-c8-upstream_leased-example.csv', markdown=footer_md)

        st.subheader("Category 9 : Downstream distribution of sold products", anchor='S3C9_DownstreamTransport')
        show_example_form(S3_BaseAsset, key='c9', title='Show example form (S3-C9: Downstream distribution of sold products)', button_text='Get example form', filename='s3-c9-downstream_transport-example.csv', markdown=footer_md)

        st.subheader("Category 10 : Processing of sold products", anchor='S3C10_ProcessingProducts')
        show_example_form(S3_BaseAsset, key='c10', title='Show example form (S3-C10: Processing sold products)', button_text='Get example form', filename='s3-c10-processing_products-example.csv', markdown=footer_md)

      with t3:
        st.subheader("Category 11 : Use of sold products", anchor='S3C11_UseOfSold')
        show_example_form(S3_BaseAsset, key='c11', title='Show example form (S3-C11: Use of sold products)', button_text='Get example form', filename='s3-c11-use_of_sold-example.csv', markdown=footer_md)
        
        st.subheader("Category 12 : End-of-life treatment of sold products", anchor='S3C12_EOLTreatment')
        show_example_form(S3_BaseAsset, key='c12', title='Show example form (S3-C12: End-of-life treatment of sold products)', button_text='Get example form', filename='s3-c12-eol-treatment-example.csv', markdown=footer_md)

        st.subheader("Category 13 : Downstream leased assets", anchor='S3C13_DownstreamLeased')
        show_example_form(S3_BaseAsset, key='c13', title='Show example form (S3-C13: Downstream leased assets)', button_text='Get example form', filename='s3-c13-downstream_leased-example.csv', markdown=footer_md)

        st.subheader("Category 14 : Franchises", anchor='S3C14_Franchise')
        show_example_form(S3_BaseAsset, key='c14', title='Show example form (S3-C14: Franchise)', button_text='Get example form', filename='s3-c14-franchise-example.csv', markdown=footer_md)


      with t4:
        t1,t2,t3 = st.tabs(['Corporate Finance', 'Consumer Finance', 'Others'])
        with t1:
          st.subheader("Category 15-1A: Listed Equity", anchor='S3C15_1A_ListedEquity')
          show_example_form(S3C15_1A_ListedEquity, title='Show example form (S3-C15-1A: Listed Equity)', button_text='Get example form', filename='s3-c15-1a-listed_equity-example.csv', markdown=footer_md)
            
          st.subheader("Category 15-1B: Unlisted Equity", anchor='S3C15_1B_UnlistedEquity')
          show_example_form(S3C15_1B_UnlistedEquity, title='Show example form (S3-C15-1B: Unlisted Equity)', button_text='Get example form', filename='s3-c15-1b-unlisted_equity-example.csv', markdown=footer_md)
              
          st.subheader("Category 15-1C: Corporate Bonds", anchor='S3C15_1C_CorporateBonds')
          show_example_form(S3C15_1C_CorporateBonds, title='Show example form (S3-C15-1C: Corporate Bonds)', button_text='Get example form', filename='s3-c15-1c-corporate_bonds-example.csv', markdown=footer_md)
              
          st.subheader("Category 15-1D: Business Loans", anchor='S3C15_1D_BusinessLoans')
          show_example_form(S3C15_1D_BusinessLoans, title='Show example form (S3-C15-1D: Business Loans)', button_text='Get example form', filename='s3-c15-1d-business_loans-example.csv', markdown=footer_md)
              
          st.subheader("Category 15-1E: Commercial Real Estate", anchor='S3C15_1E_CommercialRealEstate')
          show_example_form(S3C15_1E_CommercialRealEstate, title='Show example form (S3-C15-1E: Commercial Real Estate)', button_text='Get example form', filename='s3-c15-1e-commercial_real_estate-example.csv', markdown=footer_md)
              
        with t2:
          st.subheader("Category 15-2A: Mortgage", anchor='S3C15_2A_Mortgage')
          show_example_form(S3C15_2A_Mortgage, title='Show example form (S3-C15-2A: Mortgages)', button_text='Get example form', filename='s3-c15-2a-mortgage-example.csv', markdown=footer_md)
          
          st.subheader("Category 15-2B: Vehicle Loans", anchor='S3C15_2B_VehicleLoans')
          show_example_form(S3C15_2B_VehicleLoans, title='Show example form (S3-C15-2B: Vehicle Loans)', button_text='Get example form', filename='s3-c15-2b-vehicle_loans-example.csv', markdown=footer_md)
          
        with t3:
          st.subheader("Category 15-3: Project Finance", anchor='S3C15_3_ProjectFinance')
          show_example_form(S3C15_3_ProjectFinance, title='Show example form (S3-C15-3: Project Finance)', button_text='Get example form', filename='s3-c15-3-project_finance-example.csv', markdown=footer_md)
          
          st.subheader("Category 15-4: Emission Removals", anchor='S3C15_4_EmissionRemovals')
          show_example_form(S3C15_4_EmissionRemovals, title='Show example form (S3-C15-4: Emission Removals)', button_text='Get example form', filename='s3-c15-4-emission_removals-example.csv', markdown=footer_md)
          
          st.subheader("Category 15-5: Sovereign Debt / Government Bonds", anchor='S3C15_5_SovereignDebt')
          show_example_form(S3C15_5_SovereignDebt, title='Show example form (S3-C15-5: Sovereign Debt)', button_text='Get example form', filename='s3-c15-5-sovereign_debt-example.csv', markdown=footer_md)


    with tab3:
      t1, t2 = st.tabs(['Upload/Validate', 'Analyze uploads'])

      with t1:        
        st.info('*(For best results, upload only csv files containing matching fields from examples and keep edits to recommended default fields to minimum)*')

        with st.form('Upload CSV files'):
          uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True, help='CSV containing any relevant Scope 3 data. Categories are automatically inferred')

          if st.form_submit_button('Upload'):
            # reset everything if button is clicked
            st.session_state['s3vc_original_dfs'] = {}
            st.session_state['s3vc_dfs'] = {}
            st.session_state['s3vc_warnings'] = {}
            st.session_state['s3vc_calc_results'] = {}

            # Inferencer and df inits
            m = ModelInferencer()

            # creator inits
            partial_create_s3c15_data = partial(create_s3c15_data)

            # available models
            c15_models = [
              'S3C15_BaseAsset','S3C15_1A_ListedEquity','S3C15_1B_UnlistedEquity','S3C15_1C_CorporateBonds','S3C15_1D_BusinessLoans','S3C15_1E_CommercialRealEstate',
              'S3C15_2A_Mortgage','S3C15_2B_VehicleLoans',
              'S3C15_3_ProjectFinance','S3C15_4_EmissionRemovals','S3C15_5_SovereignDebt'
            ]
            c14_models = []
            c10_models = []

            # Loop through the uploaded files and convert to models
            for uploaded_file in uploaded_files:
              data = pd.read_csv(uploaded_file)

              if data is not None:
                df = get_dataframe(data)

                # Create models from df
                m.transform_df_to_model(df)

                # infer model from df
                inferred_model = m.infer_model_from_df(df=df)
                if inferred_model is None:
                  st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches. Please make sure you are submitting a file that closely resemble the examples.')
                  continue

                model_name = inferred_model['model']
                Model = m.available_models[model_name]    
            
                # Choose calculator based on inferred model
                if model_name in []:
                  pass 
                elif model_name in c15_models:
                  calc = S3C15_Calculator()
                  creator = partial(create_s3c15_data, Model=Model)
                else:
                  raise ValueError(f"Unknown model: {model_name}")

                try:
                  calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False)
                  result_df = calculator_to_df(calc)

                  if len(warning_list) > 0:
                    st.session_state['s3vc_warnings'][model_name] = warning_list
                  st.session_state['s3vc_original_dfs'][model_name] = df
                  st.session_state['s3vc_dfs'][model_name] = result_df
                  st.session_state['s3vc_calc_results'][model_name] = calc
                
                except Exception as e:
                  raise
        
        #-Show uploaded dfs-#
        if st.session_state['s3vc_original_dfs'] not in [{}]:
          st.subheader('Review uploaded files')

          for name, df in st.session_state['s3vc_original_dfs'].items(): # works
            if len(df) > 0:
              with st.expander(f'Show uploaded table ({name})'):
                pandas_2_AgGrid(df, theme='balham', key=f's3_{name}_aggrid')
          
          st.info('If there are no issues with your uploaded files, you may proceed to **Analyze uploads** tab')


      with t2:
        with st.expander('Show help'):
          st.markdown('Hi')

        if 's3vc_original_dfs' not in st.session_state or st.session_state['s3vc_original_dfs'] in [{}]:
          st.info('Please upload at least one valid table at "Upload/Validate" tab to continue')

        if 's3vc_original_dfs' in st.session_state and st.session_state['s3vc_original_dfs'] not in [{}]:
          with st.expander('Show uploaded table', expanded=True):
            for name, df in st.session_state['s3vc_original_dfs'].items():
              pandas_2_AgGrid(df, theme='balham', height=300, key=f's3vc_og_{name}_aggrid')

        if 'analyzed_s3vc' not in st.session_state:
          st.session_state['analyzed_s3vc'] = False
        
        analyze_button = st.button('Analyze uploaded dataframes', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis')
        if analyze_button and st.session_state['s3vc_original_dfs'] not in [{}]:
          st.session_state['analyzed_s3vc'] = True   
          st.success('Uploaded Scope 3 data tables analyzed!')

          if all(key in st.session_state for key in ['s3vc_warnings', 's3vc_dfs']) and st.session_state.get('analyzed_s3vc', True):
            with st.expander('Show warnings'):
              for name, warnings in st.session_state['s3vc_warnings'].items():
                for warn in warnings:
                  st.warning(f'{name}: {warn}')
            
            for name, df in st.session_state['s3vc_dfs'].items(): # might not need this
              with st.expander(f'Show table for analyzed **{name}**'):
                pandas_2_AgGrid(df, theme='balham', height=300, key=f's3vc_{name}_aggrid')


    with tab4:
      st.subheader('Executive Insights')

      if 's3vc_calc_results' in st.session_state and st.session_state['s3vc_calc_results'] != {}:
        res_df = st.session_state['s3vc_calc_results']
        res_df = calculators_2_df(res_df)

        pandas_2_AgGrid(res_df) # 

        fig1 = make_bar_chart(res_df, scope_col='scope', category_col='category', value_col='financed_emissions', theme='gecko5', height=300, watermark=True, legend=False, legend_dark=False)
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = make_donut_chart(res_df, group_col='category', value_col='financed_emissions', center_text='Pie chart', legend=False, theme='gecko5')
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = make_grouped_line_chart(res_df, group_col='category', value_col='financed_emissions', date_col='date', theme='gecko5', legend_dark=True)
        st.plotly_chart(fig3, use_container_width=True)


        #----------
        ts= create_line_simulation()
        st.write(ts)
        
        fig4 = make_grouped_line_chart(
          ts, 
          group_col='category', 
          value_col='value', 
          date_col='date', 
          resample_freq='Q', 
          stacked=False,
          theme='google'
        )
        st.plotly_chart(fig4, use_container_width=True)
        #-----------

        fig5 = make_sankey_chart(res_df, hierarchy_col_list=['financial_type', 'category', 'sector'], theme='google')
        st.plotly_chart(fig5, use_container_width=True)






#---
# Helpers
#---
def calculators_2_df(calculators):
  """ 
  calculators: dictionary of calculators
    Example: 
    calculators = {
      'Scope1_MobileCombustion': calculator1,
      'Scope2_IndirectEmissions': calculator2,
      # ...
    }
  """
  def get_first_number(d):
    if isinstance(d, dict):
      for value in d.values():
        if isinstance(value, (int, float)):
          return value
    return np.nan

  rows = []
  for name, calculator in calculators.items():
    scope = name.split('_')[0]  # Assuming the scope is the first part of the name
    category = name.split('_')[-1]

    if hasattr(calculator, 'calculated_emissions'):
      for key, value in calculator.calculated_emissions.items():

        # Initialize row
        row = {
          'scope': scope,
          'category': category,
        }

        input_data = value.get('input_data', {})
        for k, v in input_data.items():
          if 'description' not in k.lower() and 'uuid' not in k.lower():
            row[k] = v

        emission_data = value.get('calculated_emissions', {})
        for k, v in emission_data.items():
          if isinstance( v, (int, float, str, bool)):
            row[k] = v
          elif isinstance( v, (dict,list )):
            row[k] = get_first_number(v)
          else:
            print(f'Column {k} unable to retrieve valid value. {v} as {type(v)}')

        rows.append(row)
  
  df = pd.DataFrame(rows)
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
      df[col] = df[col].apply(json.dumps)
  return df

















 

#---
# Markdowns
#---
general_guide_md = """
- Get the recommended scopes for your sector. **:blue["Settings" >> "Show highlighted rows"]**
- Click on the links in **[:green[Table of Contents]](#s3-toc)** to redirect you to the recommended tables to fill. 
- Download the example forms. Each transaction counts as a row.
- Unless the default information conflicts with what you have, you are **:green[strongly advised]** to not edit default values for columns. 
- Cells shown as **<Blank>** indicates the field is optional, but inputting them will result in greater accuracy and reconcilation efforts.
"""

table_of_contents_md="""
- [**Category 1 : Purchased goods & services**](#S3C1_PurchasedGoods)
- [**Category 2 : Capital goods**](#S3C2_CapitalGoods)
- [**Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)**](#S3C3_EnergyRelated)
- [**Category 4 : Upstream transportation & distribution**](#S3C4_UpstreamTransport)
- [**Category 5 : Waste generated in operations**](#S3C5_WasteGenerated)
- [**Category 6 : Business and air travel**](#S3C6_BusinessTravel)
- [**Category 7 : Employee commuting**](#S3C7_EmployeeCommute)
- [**Category 8 : Upstream leased assets**](#S3C8_UpstreamLeased)
- [**Category 9 : Transportation & distribution of sold products**](#S3C9_DownstreamTransport)
- [**Category 10 : Processing of sold products**](#S3C10_ProcessingProducts)
- [**Category 11 : Use of sold products**](#S3C11_UseOfSold)
- [**Category 12 : End-of-life treatment of sold products**](#S3C12_EOLTreatment)
- [**Category 13 : Downstream leased assets**](#S3C13_DownstreamLeased)
- [**Category 14 : Franchises**](#S3C14_Franchise)
- **Category 15 : Investments**
  - 1. Corporate Finance
    - [A: Listed Equity](#S3C15_1A_ListedEquity)
    - [B: Unlisted Equity](#S3C15_1B_UnlistedEquity)
    - [C: Corporate Bonds](#S3C15_1C_CorporateBonds)
    - [D: Business Loans](#S3C15_1D_BusinessLoans)
    - [E: Commercial Real Estate](#S3C15_1E_CommercialRealEstate)
  - 2. Consumer Finance
    - [A: Mortgage](#S3C15_2A_Mortgage)
    - [B: Vehicle Loans](#S3C15_2B_VehicleLoans)
  - [3. Project Finance](#S3C15_3_ProjectFinance)
  - [4. Emission Removals](#S3C15_4_EmissionRemovals)
  - [5. Sovereign Debt / Government Bonds](#S3C15_5_SovereignDebt)
"""

