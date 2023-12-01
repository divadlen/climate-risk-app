import streamlit as st
from streamlit import session_state as state
from st_aggrid import JsCode
import streamlit_antd_components as sac
from streamlit_extras.metric_cards import style_metric_cards
    
import numpy as np
import pandas as pd
from functools import partial
from typing import List

import plotly.express as px
import plotly.graph_objects as go

from utils.globals import SECTOR_TO_CATEGORY_IDX, IDX_TO_CATEGORY_NAME
from utils.utility import get_dataframe, format_metric
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.model_df_utility import df_to_calculator, calculator_to_df, calculators_2_df
from utils.md_utility import markdown_insert_images
from utils.model_inferencer import ModelInferencer

from utils.s3vc_Misc.s3_models import *
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache
from utils.s3vc_Misc.s3_calculators import S3_Calculator
from utils.s3vc_Misc.s3_creators import *

from utils.s3vc_Misc.s3c15_models import *
from utils.s3vc_Misc.s3c15_calculators import S3C15_Calculator, create_s3c15_data


def s3vc_Page(): 
  if 'geolocator' not in state:
    state['geolocator'] = GeoLocator()
  if 'S3VC_Lookup_Cache' not in state:
    state['S3VC_Lookup_Cache'] = S3_Lookup_Cache()


  st.title('Scope 3: Value Chain')  
  if not state.get('s3_settings'):
    with st.form(key='scope_3_config'):
      valid_sectors = list(SECTOR_TO_CATEGORY_IDX.keys())
      sector = st.selectbox('Select Sector', options=valid_sectors)
      
      if st.form_submit_button('Confirm settings'):
        with st.spinner():
          state["s3_settings"] = True
          state['s3_sector'] = sector
          st.experimental_rerun()


  if 's3_settings' in state and state['s3_settings'] == True:
    tab1, tab2, tab3, tab4 = st.tabs(['Settings', 'Get Forms/Guidelines', 'Submit & Review', 'Analysis'])
    applicable_indices = SECTOR_TO_CATEGORY_IDX.get(state['s3_sector'], None)
    
    try:
      sorted_applicable_indices = sorted(list(set(applicable_indices)))
      applicable_bools = ["Highly applicable" if i in sorted_applicable_indices else "Less Applicable"  for i in range(1, 16)]        
    except:
      sorted_applicable_indices = None
      applicable_bools = ["Less applicable"] * 15

    with tab1:
      with st.form(key='scope_3_reset'):
        st.success(f"Current sector: {state['s3_sector']}")
        st.info(f'Highighted rows indicate the *recommended* categories to be covered by industry. Navigate to **Get Forms/Guidelines** or **Submit & Review** to get started!')

        df = pd.DataFrame({
          'Category': [IDX_TO_CATEGORY_NAME[i] for i in range(1,16)],
          'Applicable': applicable_bools
        })

        cellstyle_jscode = JsCode("""
        function(params){
            if (params.data.Applicable === 'Highly applicable') {
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
          del state['s3_settings']
          st.experimental_rerun() 


    with tab2:      
      st.subheader('User Guide')
      with st.expander('Show help', expanded=True):
        download_desc = 'Click on the links in Table of Contents to redirect you to the recommended tables to fill. Download the example forms. Each transaction counts as a row.'
        fill_desc = 'Each form is represented as CSV, each row is one transaction. Example 1: in "S3C15_ListedEquity" file, each holding company counts as one row. Example 2: In "S3C7_EmployeeCommute", each employee journey counts as one row (If employee uses multiple transport method, submit multiple rows for the same employee). Details at "More help" and "Visual help"'
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
        with open("resources/mds/s3vc_general_guide.md", "r") as gmd:
          readme = gmd.read()
        readme = markdown_insert_images(readme)
        st.markdown(readme, unsafe_allow_html=True) 

      st.subheader('Table of contents', anchor='s3-toc')
      with st.expander('Show table of contents', expanded=True):
        st.markdown(table_of_contents_md)
      st.divider()

      t1, t2, t3, t4 = st.tabs(['Category 1-5', 'Category 6-10', 'Category 11-14', 'Category 15: Investments'])
      with t1:
        st.subheader("Category 1 : Purchased goods & services", anchor='S3C1_PurchasedGoods')
        show_example_form(S3C1_PurchasedGoods, key='c1', title='Show example form (S3-C1: Purchased goods & services)', button_text='Get example form', filename='s3-c1-purchased_goods-example.csv', markdown=footer_md)

        st.subheader("Category 2 : Capital goods", anchor='S3C2_CapitalGoods')
        show_example_form(S3C2_CapitalGoods, key='c2', title='Show example form (S3-C2: Capital Goods)', button_text='Get example form', filename='s3-c2-capital_goods-example.csv', markdown=footer_md)

        st.subheader("Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)", anchor='S3C3_EnergyRelated')
        show_example_form(S3C3_EnergyRelated, key='c3', title='Show example form (S3-C3: Energy-related activities)', button_text='Get example form', filename='s3-c3-energy_related-example.csv', markdown=footer_md)

        st.subheader("Category 4 : Upstream transportation & distribution", anchor='S3C4_UpstreamTransport')
        show_example_form(S3C4_UpstreamTransport, key='c4', title='Show example form (S3-C4: Upstream transportation and distribution)', button_text='Get example form', filename='s3-c4-upstream_transport-example.csv', markdown=footer_md)
        
        st.subheader("Category 5 : Waste generated in operations", anchor='S3C5_WasteGenerated')
        show_example_form(S3C5_WasteGenerated, key='c5', title='Show example form (S3-C5: Waste generated in operations)', button_text='Get example form', filename='s3-c5-waste_generated-example.csv', markdown=footer_md)

      
      with t2:
        st.subheader("Category 6-1 : Business and air travel", anchor='S3C6_BusinessTravel')
        show_example_form(S3C6_1_BusinessTravel, key='c6-1', title='Show example form (S3-C6: Business and air travel)', button_text='Get example form', filename='s3-c6-1-business_travel-example.csv', markdown=footer_md)
        
        st.subheader("Category 6-2 : Business stay", anchor='S3C6_BusinessStay')
        show_example_form(S3C6_2_BusinessStay, key='c6-2', title='Show example form (S3-C6: Business stay)', button_text='Get example form', filename='s3-c6-2-business_stay-example.csv', markdown=footer_md)

        st.subheader("Category 7 : Employee commuting", anchor='S3C7_EmployeeCommute')
        show_example_form(S3C7_EmployeeCommute, key='c7', title='Show example form (S3-C7: Employee commuting)', button_text='Get example form', filename='s3-c7-employee_commute-example.csv', markdown=footer_md)

        st.subheader("Category 8-1 : Upstream leased real estate", anchor='S3C8_UpstreamLeasedEstate')
        show_example_form(S3C8_1_UpstreamLeasedEstate, key='c8-1', title='Show example form (S3-C8: Upstream leased estate)', button_text='Get example form', filename='s3-c8-upstream_leased_estate-example.csv', markdown=footer_md)

        st.subheader("Category 8-2 : Upstream leased automobile / machines", anchor='S3C8_UpstreamLeasedAuto')
        show_example_form(S3C8_2_UpstreamLeasedAuto, key='c8-2', title='Show example form (S3-C8: Upstream leased auto)', button_text='Get example form', filename='s3-c8-upstream_leased_auto-example.csv', markdown=footer_md)

        st.subheader("Category 9 : Downstream distribution of sold products", anchor='S3C9_DownstreamTransport')
        show_example_form(S3C9_DownstreamTransport, key='c9', title='Show example form (S3-C9: Downstream distribution of sold products)', button_text='Get example form', filename='s3-c9-downstream_transport-example.csv', markdown=footer_md)

        st.subheader("Category 10 : Processing of sold products", anchor='S3C10_ProcessingProducts')
        show_example_form(S3C10_ProcessingProducts, key='c10', title='Show example form (S3-C10: Processing sold products)', button_text='Get example form', filename='s3-c10-processing_products-example.csv', markdown=footer_md)

      with t3:
        st.subheader("Category 11 : Use of sold products", anchor='S3C11_UseOfSold')
        show_example_form(S3C11_UseOfSold, key='c11', title='Show example form (S3-C11: Use of sold products)', button_text='Get example form', filename='s3-c11-use_of_sold-example.csv', markdown=footer_md)
        
        st.subheader("Category 12 : End-of-life treatment of sold products", anchor='S3C12_EOLTreatment')
        show_example_form(S3C12_EOLTreatment, key='c12', title='Show example form (S3-C12: End-of-life treatment of sold products)', button_text='Get example form', filename='s3-c12-eol-treatment-example.csv', markdown=footer_md)

        st.subheader("Category 13-1 : Downstream leased estate", anchor='S3C13_DownstreamLeasedEstate')
        show_example_form(S3C13_1_DownstreamLeasedEstate, key='c13-1', title='Show example form (S3-C13: Downstream leased estate)', button_text='Get example form', filename='s3-c13-downstream_leased_estate-example.csv', markdown=footer_md)

        st.subheader("Category 13-2 : Downstream leased automobile / machines", anchor='S3C13_DownstreamLeasedAuto')
        show_example_form(S3C13_2_DownstreamLeasedAuto, key='c13-2', title='Show example form (S3-C13: Downstream leased auto)', button_text='Get example form', filename='s3-c13-downstream_leased_auto-example.csv', markdown=footer_md)

        st.subheader("Category 14 : Franchises", anchor='S3C14_Franchise')
        show_example_form(S3C14_Franchise, key='c14', title='Show example form (S3-C14: Franchise)', button_text='Get example form', filename='s3-c14-franchise-example.csv', markdown=footer_md)


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

          st.subheader("Category 15-6: Managed Investments & Client's Portfolios", anchor='S3C15_6_ManagedInvestments')
          show_example_form(S3C15_6_ManagedInvestments, title='Show example form (S3-C15-6: Managed Investments)', button_text='Get example form', filename='s3-c15-6-managed_investments-example.csv', markdown=footer_md)


    with tab3:
      t1, t2 = st.tabs(['Upload/Validate', 'Analyze uploads'])

      with t1:        
        st.info('*(For best results, upload only csv files containing matching fields from examples and keep edits to recommended default fields to minimum)*')

        with st.form('Upload CSV files'):
          uploaded_files = st.file_uploader("Upload CSV files (accepts multiple files)", type=["csv"], accept_multiple_files=True, help='CSV containing any relevant Scope 3 data. Categories are automatically inferred')

          if st.form_submit_button('Upload'):
            s3_inits = {
              's3vc_warnings': {},
              's3vc_invalid_indices': {},
              's3vc_original_dfs': {},
              's3vc_result_dfs': {},
              's3vc_calc_results': {},
            }

            # Loop to initialize variables in state if not present
            for var_name, default_value in s3_inits.items(): 
              state[var_name] = default_value # reset everything if button is clicked

            # Inferencer and df inits
            modinf = ModelInferencer()
            gl = state['geolocator']
            cache = state['S3VC_Lookup_Cache']

            s1_models = [
              'S1_FugitiveEmission', 'S1_MobileCombustion', 'S1_StationaryCombustion'
            ]

            # available models
            c15_models = [
              'S3C15_BaseAsset','S3C15_1A_ListedEquity','S3C15_1B_UnlistedEquity','S3C15_1C_CorporateBonds','S3C15_1D_BusinessLoans','S3C15_1E_CommercialRealEstate',
              'S3C15_2A_Mortgage','S3C15_2B_VehicleLoans',
              'S3C15_3_ProjectFinance','S3C15_4_EmissionRemovals','S3C15_5_SovereignDebt', 'S3C15_6_ManagedInvestments',
            ]

            # Loop through the uploaded files and convert to models
            progress_bar = st.progress(0)
            nfiles = len(uploaded_files)
            progress_idx = 1
            
            for uploaded_file in uploaded_files:
              data = pd.read_csv(uploaded_file)
              if data is not None:
                df = get_dataframe(data)

                # infer model from df
                inferred_model = modinf.infer_model_from_df(df=df)
                if inferred_model is None:
                  st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches. Please make sure you are submitting a file that closely resemble the examples.')
                  continue

                model_name = inferred_model['model']
                Model = modinf.available_models[model_name]

                # Store the filename with the model name
                if 'model_filenames' not in state:
                  state['model_filenames'] = {}
                state['model_filenames'][model_name] = uploaded_file.name
            
                # Choose calculator based on inferred model
                if model_name in s1_models:
                  st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} should be submitted to Scope 1. Skipping...')
                  continue

                if model_name in c15_models:
                  calc = S3C15_Calculator()
                  creator = partial(create_s3c15_data, Model=Model) # creator function to pass df rows as Pydantic Models to Calculator

                else:
                  CREATOR_FUNCTIONS = {
                      'S3C1_PurchasedGoods': partial( create_s3c1_data, Model=Model, cache=cache ),
                      'S3C2_CapitalGoods': partial( create_s3c2_data, Model=Model, cache=cache ),
                      'S3C3_EnergyRelated': partial( create_s3c3_data, Model=Model, cache=cache ),
                      'S3C4_UpstreamTransport': partial( create_s3c4_data, Model=Model, cache=cache ),
                      'S3C5_WasteGenerated': partial( create_s3c5_data, Model=Model, cache=cache ),
                      
                      'S3C6_1_BusinessTravel': partial( create_s3c6_1_data, Model=Model, cache=cache ),
                      'S3C6_2_BusinessStay': partial( create_s3c6_2_data, Model=Model, cache=cache ),
                      
                      'S3C7_EmployeeCommute': partial( create_s3c7_data, Model=Model, cache=cache ),
                    
                      'S3C8_1_UpstreamLeasedEstate': partial( create_s3c8_1_data, Model=Model, cache=cache, geolocator=gl ),
                      'S3C8_2_UpstreamLeasedAuto': partial( create_s3c8_2_data, Model=Model, cache=cache ),

                      'S3C9_DownstreamTransport':partial( create_s3c9_data, Model=Model, cache=cache ),
                      'S3C10_ProcessingProducts': partial( create_s3c10_data, Model=Model, cache=cache ),
                      'S3C11_UseOfSold': partial( create_s3c11_data, Model=Model, cache=cache ),
                      'S3C12_EOLTreatment': partial( create_s3c12_data, Model=Model, cache=cache ),

                      'S3C13_1_DownstreamLeasedEstate': partial( create_s3c13_1_data, Model=Model, cache=cache, geolocator=gl ),
                      'S3C13_2_DownstreamLeasedAuto': partial( create_s3c13_2_data, Model=Model, cache=cache ),             
                      
                      'S3C14_Franchise': partial( create_s3c14_data, Model=Model, cache=cache, geolocator=gl ),
                  }
                  calc = S3_Calculator(cache=cache)
                  creator = CREATOR_FUNCTIONS[model_name]
                  
                try:
                  calc, warning_list, invalid_indices = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False, return_invalid_indices=True)
                  result_df = calculator_to_df(calc)

                  if len(warning_list) > 0:
                    state['s3vc_warnings'][model_name] = warning_list
                    state['s3vc_invalid_indices'][model_name] = invalid_indices
                  state['s3vc_original_dfs'][model_name] = df
                  state['s3vc_result_dfs'][model_name] = result_df
                  state['s3vc_calc_results'][model_name] = calc
                
                except Exception as e:
                  raise
        
                # update progress bar
                progress_pct = progress_idx / nfiles
                progress_bar.progress(progress_pct)
                progress_idx += 1

        #-Show uploaded dfs-#
        if state['s3vc_original_dfs'] not in [{}]:
          st.subheader('Review uploaded files')

          for name, df in state['s3vc_original_dfs'].items(): # works
            if len(df) > 0:
              with st.expander(f'Show uploaded table ({name})'):
                pandas_2_AgGrid(df, theme='balham', key=f's3_{name}_aggrid')
          
          st.info('If there are no issues with your uploaded files, you may proceed to **Analyze uploads** tab')


      with t2:
        if 's3vc_original_dfs' not in state or state['s3vc_original_dfs'] in [{}]:
          st.info('Please upload at least one valid table at "Upload/Validate" tab to continue')

        if 's3vc_original_dfs' in state and state['s3vc_original_dfs'] not in [{}]:
          with st.expander('Show uploaded table', expanded=True):
            for name, df in state['s3vc_original_dfs'].items():
              pandas_2_AgGrid(df.head(20), theme='balham', height=300, key=f's3vc_og_{name}_aggrid')

        if 'analyzed_s3vc' not in state:
          state['analyzed_s3vc'] = False
        
        analyze_button = st.button('Analyze uploaded dataframes', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis')
        if analyze_button and state['s3vc_original_dfs'] not in [{}]:
          state['analyzed_s3vc'] = True   
          st.success('Uploaded Scope 3 data tables analyzed!')

          if all(key in state for key in ['s3vc_warnings', 's3vc_original_dfs']) and state.get('analyzed_s3vc', True):
            with st.expander('Show warnings'):
              for name, warnings in state['s3vc_warnings'].items():
                for warn in warnings:
                  st.warning(f'{name}: {warn}')

              for name, df in state['s3vc_original_dfs'].items():
                df = df.replace('<Blank>', None)
                df = df.replace('<To fill>', None)
                df = df.replace(np.nan, None)
                pandas_2_AgGrid(
                  df, theme='balham', height=300, key=f's3vc_warn_{name}_aggrid',
                  highlighted_rows=state['s3vc_invalid_indices'].get(name, [])  # Returns an empty list if 'name' is not in the dictionary
                )
            
            for name, df in state['s3vc_result_dfs'].items(): # might not need this
              with st.expander(f'Show table for analyzed **{name}**'):
                pandas_2_AgGrid(df, theme='balham', height=300, key=f's3vc_{name}_aggrid')


    with tab4:
      st.subheader('Executive Insights')
      if 's3vc_calc_results' not in state or state['s3vc_calc_results'] == {}:
        st.error('Nothing to display here. Have you uploaded or analyzed your uploaded files?')

      if 's3vc_calc_results' in state and state['s3vc_calc_results'] != {}:
        res_df = state['s3vc_calc_results'] # key: Model name, val: Calculator
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






#---
# Helpers
#---
def emissionOverviewPart(df):      
    # Global styling
    style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

    total_s3 = df[df['scope'] == 3]['emission_result'].sum()
    st.metric(label="Scope 3 Emissions", value=format_metric(total_s3))
    st.divider()


    st.subheader('Top contributors')
    # Group DataFrame by selected option, sum, then sort
    grouped_df = df.groupby('category_name')['emission_result'].sum().reset_index()
    sorted_df = grouped_df.sort_values('emission_result', ascending=False)
    sorted_df['delta'] = round( sorted_df['emission_result'].pct_change(-1).fillna(0) * 100, 2)

    # Limit to top 10 and combine the rest as 'Others'
    top_10_df = sorted_df.head(10)
    others_sum = sorted_df.iloc[10:]['emission_result'].sum()
    others_delta = sorted_df.iloc[9]['emission_result'] - others_sum if len(sorted_df) > 10 else 0
    others_df = pd.DataFrame({'category_name': ['Others'], 'emission_result': [others_sum], 'delta': [others_delta]})
    top_10_df = pd.concat([top_10_df, others_df], ignore_index=True)

    c1, c2 = st.columns([1, 3])
    with c1:
      for index, row in top_10_df.head(5).iterrows():
        st.metric(label=f"{row['category_name']} Emissions", value=format_metric(row['emission_result']), delta=f"{row['delta']}%")

    # Vertical Bar Chart with Cumulative Sum
    total_emission = top_10_df['emission_result'].sum()
    top_10_df['cum_sum'] = top_10_df['emission_result'].cumsum()
    top_10_df['cum_sum_percent'] = (top_10_df['cum_sum'] / total_emission) * 100

    fig = go.Figure()
    for index, row in top_10_df.iterrows():
      fig.add_trace(go.Bar(
        x=[row['category_name']],  # x should be a list or array
        y=[row['emission_result']],  # y should also be a list or array
        name=str(row['category_name']),
        yaxis='y1',
        hovertemplate=f"%{{value:.2f}} kg"
      ))

    # Cumulative Sum Line
    fig.add_trace(go.Scatter(
      x=top_10_df['category_name'],
      y=top_10_df['cum_sum_percent'],
      mode='lines+markers',
      name='Cumulative Sum (%)',
      yaxis='y2',
      hovertemplate ='%{y:.2f} %',
    ))

    # Update layout
    fig.update_layout(
      title='',
      xaxis_title=f'<b>Category</b>',
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
  - [6. Managed Investments](#S3C15_6_ManagedInvestments)
"""

footer_md = """*(<Blank> and <To fill> are optional. <To fill> indicates optional fields that can affect calculations. Blue indicates REQUIRED fields with recommended default values. Orange indicates REQUIRED fields.)*"""
