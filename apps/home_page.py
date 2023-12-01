import streamlit as st
from streamlit import session_state as state
from st_aggrid import AgGrid, AgGridTheme, GridOptionsBuilder, JsCode, DataReturnMode

import pandas as pd
from functools import partial

from utils.utility import get_dataframe
from utils.model_inferencer import ModelInferencer
from utils.geolocator import GeoLocator
from utils.model_df_utility import df_to_calculator, calculator_to_df, calculators_2_df

from utils.s1de_Misc.s1_calculators import S1_Calculator
from utils.s2ie_Misc.s2_calculators import S2_Calculator
from utils.s3vc_Misc.s3_calculators import S3_Calculator
from utils.s3vc_Misc.s3c15_calculators import S3C15_Calculator, create_s3c15_data

from utils.s1de_Misc.s1_creators import *
from utils.s2ie_Misc.s2_creators import create_s2pp_data
from utils.s3vc_Misc.s3_creators import *
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache

def homePage():
  st.title('Welcome to Trace')
  st.divider()

  st.subheader('Quick Access')
  st.info(qa_md)
  with st.form('Upload CSV files'):
    uploaded_files = st.file_uploader("Upload CSV files (accepts multiple files)", type=["csv"], accept_multiple_files=True, help='CSV containing any Scope1, Scope2, Scope3 data.')

    if st.form_submit_button('Upload'):
      if len(uploaded_files) > 40:
        st.error('Number of uploaded files exceeded limit of 40!')
        st.stop()
      
      if 'geolocator' not in state:
        state['geolocator'] = GeoLocator()
      if 'S3VC_Lookup_Cache' not in state:
        state['S3VC_Lookup_Cache'] = S3_Lookup_Cache()

      # Inferencer and df inits
      modinf = ModelInferencer()
      gl = state['geolocator']
      cache = state['S3VC_Lookup_Cache']

      # Loop through the uploaded files and convert to models
      progress_bar = st.progress(0)
      nfiles = len(uploaded_files)
      progress_idx = 1

      for uploaded_file in uploaded_files:
        data = pd.read_csv(uploaded_file)
        
        if data is not None:
          df = get_dataframe(data)
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

          if model_name in s1_models:
            s1_inits = {
              's1de_calc_results': {},
              's1de_warnings': {},
              's1de_original_dfs': {},
              's1de_result_dfs': {},
            }

            # Loop to initialize variables in state if not present
            for var_name, default_value in s1_inits.items():
              if var_name not in state:
                state[var_name] = default_value
            
            CREATOR_FUNCTIONS = {
              'S1_MobileCombustion': partial( create_s1mc_data, Model=Model, cache=cache ),
              'S1_StationaryCombustion': partial( create_s1sc_data, Model=Model, cache=cache ),
              'S1_FugitiveEmission': partial( create_s1fe_data, Model=Model, cache=cache ),
            }

            calc = S1_Calculator(cache=cache)
            creator = CREATOR_FUNCTIONS[model_name]  
            calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False)   
            result_df = calculator_to_df(calc)

            if len(warning_list) > 0:
              state['s1de_warnings'][model_name] = warning_list
            state['s1de_original_dfs'][model_name] = df
            state['s1de_result_dfs'][model_name] = result_df # required to display validated table in S1 tab, when upload vector from home.
            state['s1de_calc_results'][model_name] = calc

          elif model_name in s2_models:
            s2_inits = {
              's2ie_calc_results': {},
              's2ie_warnings': {},
              's2ie_original_dfs': {},
              's2ie_result_dfs': {},
            }

            # Loop to initialize variables in state if not present
            for var_name, default_value in s2_inits.items():
              if var_name not in state:
                state[var_name] = default_value

            CREATOR_FUNCTIONS = {
              'S2_PurchasedPower': partial( create_s2pp_data, Model=Model, cache=cache, geolocator=gl ),
            }

            calc = S2_Calculator(cache=cache)
            creator = CREATOR_FUNCTIONS[model_name]
            calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=True)
            result_df = calculator_to_df(calc)

            if len(warning_list) > 0:
              state['s2ie_warnings'][model_name] = warning_list
            state['s2ie_original_dfs'][model_name] = df
            state['s2ie_result_dfs'][model_name] = result_df # required to display validated table in S2 tab, when upload vector from home.
            state['s2ie_calc_results'][model_name] = calc

          elif model_name in c15_models:
            if 's3vc_calc_results' not in state:
              state['s3vc_calc_results'] = {}
            
            calc = S3C15_Calculator()
            creator = partial(create_s3c15_data, Model=Model) 
            calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False)
            state['s3vc_calc_results'][model_name] = calc

          else:
            if 's3vc_calc_results' not in state:
              state['s3vc_calc_results'] = {}

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
            calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False)
            state['s3vc_calc_results'][model_name] = calc  

          # update progress bar
          progress_pct = progress_idx / nfiles
          progress_bar.progress(progress_pct)
          progress_idx += 1 

  
  if any(state.get(calc_result) for calc_result in ['s1de_calc_results', 's2ie_calc_results', 's3vc_calc_results']):
    with st.expander('View Processed Files', expanded=True):
      df_for_grid = get_df_from_uploads()
      grid = create_grid_from_upload_df(df_for_grid)

      if st.button('Delete selected'):
        aggrid_row_delete(grid)
        
        if st.__version__ >= '1.28.0':
          st.rerun() # experimental deprecated in 2024-04-01
        else:
          st.experimental_rerun()
  
  else:
    st.info('File not yet uploaded or all models have been deleted.')


#------
# AG Grid helper
#-----
def get_df_from_uploads() -> pd.DataFrame:
  data = []
  for calc_result in ['s1de_calc_results', 's2ie_calc_results', 's3vc_calc_results']:
    if calc_result in state:
      for model_name in state[calc_result]:
        filename = state['model_filenames'].get(model_name, 'Unknown')  # Get the filename or default to 'Unknown'
        data.append({
          'Filename': filename,
          'Model Name': model_name, 
          'Status': 'Processed'}
        )
  return pd.DataFrame(data)


def aggrid_row_delete(grid):
  """ 
  Deletes selected rows from AG Grid and associated state variables.
  """
  selected_rows = grid['selected_rows']
  prefixes = ['s1de', 's2ie', 's3vc']
  suffixes = ['calc_results', 'warnings', 'original_dfs', 'result_dfs']

  for row in selected_rows:
    model_name = row['Model Name']

    for prefix in prefixes:
      for suffix in suffixes:
        key = f'{prefix}_{suffix}' # example: s1de_warnings
        try:
          if model_name in state[key]:
            del state[key][model_name] # example: state['s1de_warnings']['S1MobileCombustion']
        except KeyError:
          continue



def create_grid_from_upload_df(df, theme='streamlit'):
  valid_themes= ['streamlit', 'alpine', 'balham', 'material']
  if theme not in valid_themes:
    raise Exception(f'Theme not in {valid_themes}')
  
  custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}} # allows page arrows to be shown

  gd = GridOptionsBuilder.from_dataframe(df)
  gd.configure_column("Select", checkboxSelection=True, headerCheckboxSelection=True, pinned="left", width=50) # add a check column
  gd.configure_selection(selection_mode='multiple', suppressRowClickSelection=True)
  gd.configure_pagination(enabled=True)
  gridOptions = gd.build()
  grid = AgGrid(
    df,
    custom_css=custom_css,
    gridOptions=gridOptions,
    data_return_mode=DataReturnMode.AS_INPUT, 
    update_on='MANUAL',
    theme=theme,
    enable_enterprise_modules=False, # unless we pay aggrid
    allow_unsafe_jscode=True,
    height=300,
    width='100%',
  )
  return grid





all_models = list(ModelInferencer().available_models.keys())
s1_models = [
  'S1_FugitiveEmission', 'S1_MobileCombustion', 'S1_StationaryCombustion'
]
s2_models = ['S2_PurchasedPower']
c15_models =[
  'S3C15_BaseAsset','S3C15_1A_ListedEquity','S3C15_1B_UnlistedEquity','S3C15_1C_CorporateBonds','S3C15_1D_BusinessLoans','S3C15_1E_CommercialRealEstate',
  'S3C15_2A_Mortgage','S3C15_2B_VehicleLoans',
  'S3C15_3_ProjectFinance','S3C15_4_EmissionRemovals','S3C15_5_SovereignDebt', 'S3C15_6_ManagedInvestments',
]

qa_md = """
Already used to our navigation? Here is a one-stop place to upload your relevant GHG accounting tables.
"""
