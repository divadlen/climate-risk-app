import streamlit as st
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

from streamlit_sortables import sort_items
from streamlit_extras.metric_cards import style_metric_cards

import math
import numpy as np
import pandas as pd
import json
import re

import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio

from utils.charting import initialize_plotly_themes \
    ,make_bar_chart, make_donut_chart, make_grouped_line_chart, make_sankey_chart, make_sunburst_chart



def main_dash_Page():
  
  # Global styling
  style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

  st.title('Emissions Executive Summary')
  tab1, tab2 = st.tabs(["Overall Emissions", "Financed Emissions"])

  with tab1:
    dfs_to_concat = []

    if 's1de_calc_results' in st.session_state and st.session_state['s1de_calc_results'] != {}:
      s1_res = st.session_state['s1de_calc_results']
      s1_df = calculators_2_df(s1_res)
      dfs_to_concat.append(s1_df)
    else:
      st.error('Calculated results for Scope 1 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    if 's2ie_calc_results' in st.session_state and st.session_state['s2ie_calc_results'] != {}:
      s2_res = st.session_state['s2ie_calc_results']     
      s2_df = calculators_2_df(s2_res)
      s2_df['data_quality'] = 4
      dfs_to_concat.append(s2_df)
    else:
      st.error('Calculated results for Scope 2 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    if 's3vc_calc_results' in st.session_state and st.session_state['s3vc_calc_results'] != {}:
      s3_res = st.session_state['s3vc_calc_results'] # key: Model name, val: Calculator
      s3_df = calculators_2_df(s3_res) # convert each k/v to df
      dfs_to_concat.append(s3_df)
    else:
      st.error('Calculated results for Scope 3 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    # st.write(pd.concat(dfs_to_concat, ignore_index=True)) # 

    standardized_dfs = [standardize_scope_df(df) for df in dfs_to_concat]
    if standardized_dfs:
      

      df = pd.concat(standardized_dfs, ignore_index=True)
      df = standardize_merged_df(df)

      st.write(df.head().to_dict(orient='records')) # 
      st.write(df)

      with st.expander('Expand'):
        st.subheader('Overall')

        c1, c2, c3 = st.columns([1,2,1])
        with c1:
          with st.container():
            st.metric(label="Emissions Overview Total", value=df['emission_result'].sum(), delta=53)


        with c2:
          bar1 = make_bar_chart(df, scope_col=None, category_col='category_name', year_col=None, value_col='emission_result', theme='google', title='YEs')
          st.plotly_chart(bar1, use_container_width=True)

        with c3:
          pass

      # Emissions Overview
      emissionOverviewPart(df)

      # Category Performance
      categoryPerformancePart(df)

      # Contributor Analysis
      contributorAnalysisPart(df)

      # Hierarchal Flow
      hierarchalFlowPart(df)

      # Data quality
      dataQualityPart(df)








      # # create bar chart
      # fig1 = make_bar_chart(df, scope_col='scope', value_col='emission_result', theme='google')
      # st.plotly_chart(fig1, use_container_width=True)

      # # create donut chart 
      # fig2 = make_donut_chart(df, group_col='scope', value_col='emission_result', hole=0.5, center_text='Emission Result', theme='gecko_v2')
      # st.plotly_chart(fig2, use_container_width=True)




      # # create sunburst chart
      # hierarchy_list = ['scope', 'category_name']
      # fig = make_sunburst_chart(df, hierarchy_list=hierarchy_list, value_col='emission_result')
      # st.plotly_chart(fig, use_container_width=True)



    else:
      st.error('No data available.')



  with tab2:
    pass






def emissionOverviewPart(df):      
    def format_metric(value) -> str:
        if value <= 0:
            return "0 g CO2e"
        elif value < 1:
            return f"{value * 1000:.0f} g CO2e"
        elif value < 1000:  # Less than 1 Ton
            return f"{value:.2f} Kg CO2e"
        elif value < 1e6:  # Less than 1 million
            return f"{value / 1000:.2f} Ton CO2e"
        elif value < 1e9:  # Less than 1 billion
            return f"{value / 1e6:.2f}K Ton CO2e"
        elif value < 1e12:  # Less than 1 trillion
            return f"{value / 1e9:.2f}M Ton CO2e"
        elif value < 1e15:  # Less than 1 quadrillion
            return f"{value / 1e12:.2f}B Ton CO2e"
        else:
            exponent = int(math.log10(value))
            return f"{value / 10**exponent:.2f}e{exponent} Ton CO2e"

    with st.expander('Emissions Overview'):
      c1, c2, c3 = st.columns([1, 1, 1])
      
      with c1:
          total_scope1 = df[df['scope'] == 1]['emission_result'].sum()
          st.metric(label="Scope 1 Emissions", value=format_metric(total_scope1))
      with c2:
          total_scope2 = df[df['scope'] == 2]['emission_result'].sum()
          st.metric(label="Scope 2 Emissions", value=format_metric(total_scope2))
      with c3:
          total_scope3 = df[df['scope'] == 3]['emission_result'].sum()
          st.metric(label="Scope 3 Emissions", value=format_metric(total_scope3))

      temp = df.copy()
      temp['scope_str'] = "Scope " + temp['scope'].astype(str)
      donut_fig = make_donut_chart(temp, group_col='scope_str', value_col='emission_result', hole=0.5, theme='gecko5', center_text='<b>Total CO2e</b>', horizontal_legend=True)
      st.plotly_chart(donut_fig, use_container_width=True)

              
      # Upstream and Downstream percentages
      total_current = df[df['stream'] == 'Current']['emission_result'].sum()
      total_upstream = df[df['stream'] == 'Upstream']['emission_result'].sum()
      total_downstream = df[df['stream'] == 'Downstream']['emission_result'].sum()

      total = total_upstream + total_downstream + total_current
      upstream_percent = (total_upstream / total) * 100
      current_percent = (total_current / total) * 100
      downstream_percent = (total_downstream / total) * 100

      # Create a DataFrame for the bar chart
      bar_df = pd.DataFrame({
          'Stream': ['Upstream', 'Current', 'Downstream'],
          'Percentage': [upstream_percent, current_percent, downstream_percent]
      })

      # Initialize the figure
      fig = go.Figure()

      # Add traces
      for index, row in bar_df.iterrows():
          fig.add_trace(go.Bar(
              x=[row['Percentage']],
              name=row['Stream'],
              orientation='h'
          ))

      # Update layout
      fig.update_layout(
          title='Upstream vs Downstream Emissions',
          xaxis=dict(title='Percentage'),
          yaxis=dict(title='', tickvals=[]),
          barmode='stack',
          height=250,
          template='gecko7',
          legend=dict(
            orientation='h',
            x=0.5,
            y=1,
            xanchor='center',
            yanchor='bottom'
          )
      )
      st.plotly_chart(fig, use_container_width=True)


def categoryPerformancePart(df):
  with st.expander('Category Breakdown'):
    c1,c2 = st.columns([1,1])

    with c1:
      show_legend = st.selectbox('Show legend', options=[True, False], key='show_legend_category')
    with c2:
      show_percent = st.selectbox('Show as percent (%)', options=[False, True], key='show_percent_category')

    categories = df['category_name'].unique()
    for scope in [1, 2, 3]:
      scope_df = df[df['scope'] == scope]
    
      if len(scope_df) < 1:
        continue

      fig = make_bar_chart(
        scope_df, scope_col=None, category_col='category_name', year_col=None, value_col='emission_result', 
        percent=show_percent, legend=show_legend,
        theme='gecko7', title=f'Scope {scope}', watermark=False, horizontal_legend=True, legend_sort_numeric=True, auto_adjust_height=True
      )
      st.plotly_chart(fig, use_container_width=True)


def hierarchalFlowPart(df):
  def make_sankey_chart(df, hierarchy_col_list, value_col):
      # Create unique lists for each hierarchy level and combine them
      all_labels = []
      for col in hierarchy_col_list:
          unique_labels = df[col].unique().tolist()
          all_labels += unique_labels

      # Create an index mapping for all labels
      label_idx = {label: i for i, label in enumerate(all_labels)}

      # Initialize source, target, and value lists for Sankey links
      sources = []
      targets = []
      values = []

      # Populate source, target, and value lists
      for _, row in df.iterrows():
          for i in range(len(hierarchy_col_list) - 1):
              source_col = hierarchy_col_list[i]
              target_col = hierarchy_col_list[i + 1]
              value = row[value_col]

              sources.append(label_idx[row[source_col]])
              targets.append(label_idx[row[target_col]])
              values.append(value)

      # Create the Sankey diagram
      fig = go.Figure(go.Sankey(
          node=dict(
              pad=20,
              thickness=20,
              line=dict(color='black', width=1),
              label=all_labels
          ),
          link=dict(
              source=sources,
              target=targets,
              value=values,
              color='lightgrey'
          )
      ))

      fig.update_layout(title_text="<b>Emissions Flow</b>", title_x=0.5, font_size=10, height=700)
      fig.update_layout(template='google')
      fig.update_layout(images=st.session_state.watermark_settings)
      fig.update_layout(showlegend=False)
      return fig
  

  with st.expander('Emissions Flow Discovery'):
    categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
    exclude_columns = {'uuid', 'date', 'category'}
    categorical_columns = list(categorical_columns - exclude_columns)

    with st.form(key='hierarchy_form'):
      original_items = [
        {'header': 'Available fields',  'items': categorical_columns},
        {'header': 'Hierarchy Order', 'items': []}
      ]
      sorted_items = sort_items(original_items, multi_containers=True)
      hierarchy_list = [item for item in sorted_items if item['header'] == 'Hierarchy Order'][0]['items']
      submit_button = st.form_submit_button('Update Charts')

    if submit_button:
      if len(hierarchy_list) < 2:
        st.error('Hierarchy list must have at least 2 columns!') # you will still generate an empty sankey due to "hierarchy_list" modified

      else:
        temp = df.copy()
        original_len = len(temp)

        for col in hierarchy_list:
          temp = temp[temp[col].notna()]
          removed_rows = original_len - len(temp)
          
          if original_len > 0 and removed_rows > 0:
            if removed_rows >= original_len:
              st.error(f'Selected column {col} is incompatible for the current flowchart and will result in empty dataset.')
              original_len -= removed_rows
            else:
              st.info(f'{removed_rows} rows were removed from {original_len} during subsetting for "{col}". Remaining datapoints: {original_len - removed_rows}')
              original_len -= removed_rows

        if len(temp) == 0:
          st.warning("Unable to display emission flow chart under this combination of hierarchy. Please adjust the columns.")  
        else:
          st.session_state['hierarchal_flow_df'] = temp
          st.session_state['hierarchy_list'] = hierarchy_list

    if 'hierarchal_flow_df' in st.session_state and 'hierarchy_list' in st.session_state:
      sankey_fig = make_sankey_chart(st.session_state['hierarchal_flow_df'], hierarchy_col_list=st.session_state['hierarchy_list'], value_col='emission_result')
      st.plotly_chart(sankey_fig, use_container_width=True)



def contributorAnalysisPart(df):
  with st.expander('Contributor Analysis'):
      # Get only categorical or object columns
      categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
      exclude_columns = {'uuid', 'date', 'category'}
      categorical_columns = list(categorical_columns - exclude_columns)

      # Select category
      c1,c2 = st.columns([1,1])
      with c1:
        show_legend = st.selectbox('Show legend', options=[True, False], key='show_legend_contribute')
      with c2:
        default_index_category = categorical_columns.index('category_name') if 'category_name' in categorical_columns else 0
        selected_category = st.selectbox('Select category', categorical_columns, key='selected_category_contribute', index=default_index_category)

      # Group DataFrame by selected option and sum the emission_result
      grouped_df = df.groupby(selected_category)['emission_result'].sum().reset_index()

      # Sort DataFrame by emission_result
      sorted_df = grouped_df.sort_values('emission_result', ascending=False)

      # Vertical Bar Chart with Cumulative Sum
      total_emission = sorted_df['emission_result'].sum()
      sorted_df['cum_sum'] = sorted_df['emission_result'].cumsum()
      sorted_df['cum_sum_percent'] = (sorted_df['cum_sum'] / total_emission) * 100

      fig_v = go.Figure()

      # Emission Result Bar
      for index, row in sorted_df.iterrows():
          fig_v.add_trace(go.Bar(
              x=[row[selected_category]],  # x should be a list or array
              y=[row['emission_result']],  # y should also be a list or array
              name=str(row[selected_category]),
              yaxis='y1'
          ))

      # Cumulative Sum Line
      fig_v.add_trace(go.Scatter(
          x=sorted_df[selected_category],
          y=sorted_df['cum_sum_percent'],
          mode='lines+markers',
          name='Cumulative Sum (%)',
          yaxis='y2'
      ))

      # Update layout
      fig_v.update_layout(
          title='',
          xaxis_title=f'<b>{selected_category}</b>',
          yaxis=dict(title='<b>Emission Result</b>'),
          yaxis2=dict(
              title='<b>Cumulative Sum (%)</b>',
              overlaying='y',
              side='right',
              range=[0, 100]
          ),
          height=600,
          template='google',
          legend=dict(
            orientation='h', title=None,
            x=0.5, y=1, xanchor='center', yanchor='bottom'
          ),
          showlegend=show_legend
      )
      st.plotly_chart(fig_v, use_container_width=True)


def dataQualityPart(df):
  with st.expander('Data Quality Report'):
    # category only
    categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
    exclude_columns = {'uuid', 'date'}
    categorical_columns = list(categorical_columns - exclude_columns)

    # numeric only
    numerical_columns = set(df.select_dtypes(include=['float']).columns)
    exclude_columns = {'data_quality', 'scope', 'category', 'state', 'country', 'lat', 'lon'}
    numerical_columns = list(numerical_columns - exclude_columns)

    # Select category
    c1,c2 = st.columns([1,1])
    with c1:
      default_index_numeric = numerical_columns.index('emission_result') if 'emission_result' in numerical_columns else 0
      selected_numeric = st.selectbox('Select Y-axis', numerical_columns, index=default_index_numeric)
    with c2:
      default_index_category = categorical_columns.index('category_name') if 'category_name' in categorical_columns else 0
      selected_category = st.selectbox('Select category', categorical_columns, key='selected_category_dq', index=default_index_category)

    temp = df.copy()
    min_val = np.nanmin(temp['emission_result'])
    max_val = np.nanmax(temp['emission_result'])
    temp['log_res'] = np.where(
      temp['emission_result'].notna(),
      (np.log(temp['emission_result'] + 1) - np.log(min_val + 1)) / (np.log(max_val + 1) - np.log(min_val + 1)),
      np.nan
    )

    xdata = 'data_quality'
    sdata = 'emission_result'

    fig = px.scatter(
      temp, x=xdata, y=selected_numeric, color=selected_category, 
      size='log_res', 
      log_y=True,
      opacity=0.6
    )

    fig.update_layout(
      title='Data Gap Discovery',
      xaxis_title=f'<b>{xdata}</b>',
      yaxis=dict(title=f'<b>{selected_numeric}</b>'),
      height=600,
      template='google',
      legend=dict(
        orientation='h', title=None,
        x=0.5, y=1, xanchor='center', yanchor='bottom'
      )
    )
    fig.update_xaxes(range=[0, 5])
    st.plotly_chart(fig, use_container_width=True)




































#---
# Helpers
#---
@st.cache_data()
def standardize_scope_df(df):
  """ 
  df: 
    Merged df from s1, s2, s3 calculation results.
  """
  cols = [
    'uuid', 'date',
    'scope', 'category', 'category_name', 'stream',
    'emission_result', 'most_reliable_co2e', 'financed_emissions', 'emission_removals',
    'data_quality',

    # name
    'product_name', 'distributor_name', 'process_name', 'supplier_name',

    # asset status
    'ownership_status', 'ownership_share',

    # location
    'country', 'state', 'company_name', 'asset_class'  

    # types
    'refrigerant_type', 'vehicle_type', 'freight_type', 'fuel_type', 'waste_type'
  ]

  selected_cols = [col for col in cols if col in df.columns]
  df = df[selected_cols]
  return df


@st.cache_data()
def standardize_merged_df(df):
  """ 
  Different dfs soured from s1, s2, s3 may have different names given for their emission column. 
  This function tries to standardize them into a same column name,
  """
  def standardize_emission_results(df, alt_col_name:str):
    df['emission_result'] = df.apply(
      lambda row: row[alt_col_name] if pd.isna(row['emission_result']) and not pd.isna(row[alt_col_name]) else row['emission_result'],
      axis=1
    )
    df = df.drop(alt_col_name, axis=1)
    return df
  
  alt_col_names = ['most_reliable_co2e', 'financed_emissions', 'emission_removals']
  for name in alt_col_names:
    if name in df.columns:
      df = standardize_emission_results(df, alt_col_name=name)

  return df



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
  def camel_case_to_natural(camel_case_str):
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', camel_case_str)


  def extract_scope_and_category(name):
      scope_match = re.search(r'S(\d+)', name)
      category_match = re.search(r'C(\d+)', name)
      
      scope = int(scope_match.group(1)) if scope_match else None
      category = int(category_match.group(1)) if category_match else None
      category_name = camel_case_to_natural(name.split('_')[-1])
      return scope, category, category_name
  

  def get_stream_status(scope, category):
      if scope in [1, 2]:
          return "Current"
      if category in [None, np.nan]:
          return None
      if category < 9:
          return "Upstream"
      return "Downstream"
  

  def get_first_number(d):
    if isinstance(d, dict):
      for value in d.values():
        if isinstance(value, (int, float)):
          return value
    return np.nan

  rows = []
  for name, calculator in calculators.items():
    scope, category, category_name = extract_scope_and_category(name)    
    stream = get_stream_status(scope=scope, category=category)

    if hasattr(calculator, 'calculated_emissions'):
      for key, value in calculator.calculated_emissions.items():

        # Initialize row
        if category is None or category_name is None:
          formatted_category_name = None
        if category is None:
          formatted_category_name = f"C0: {category_name}"
        else:
          formatted_category_name = f"C{category}: {category_name}"

        row = {
          'scope': scope,
          'category': category,
          'category_name': formatted_category_name,
          'stream': stream
        }
        input_data = value.get('input_data', {})

        for k, v in input_data.items():
          if 'description' not in k.lower(): # get rid of description cols
            row[k] = v

        emission_data = value.get('calculated_emissions', {})
        
        for k, v in emission_data.items():
          if isinstance( v, (int, float, str, bool)):
            row[k] = v
          elif isinstance( v, (dict)):
            row[k] = get_first_number(v)
          elif isinstance( v, list ):
            try:
              row[k] = v[0]
            except:
              row[k] = {}
          else:
            print(f'Column {k} unable to retrieve valid value. {v} as {type(v)}')

        rows.append(row)
  
  df = pd.DataFrame(rows)
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
      df[col] = df[col].apply(json.dumps)

  return df