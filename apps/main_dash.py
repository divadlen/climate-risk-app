import streamlit as st
from streamlit import session_state as state
from streamlit_sortables import sort_items
from streamlit_extras.metric_cards import style_metric_cards

import re
import math
import numpy as np
import pandas as pd
from PIL import Image

import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from utils.utility import format_metric, convert_df, humanize_field
from utils.display_utility import pandas_2_AgGrid
from utils.model_df_utility import calculators_2_df
from utils.charting import make_donut_chart, sort_str_column_numeric


#  pandas warning so annoying
import warnings
warnings.filterwarnings("ignore")


def main_dash_Page():
  
  # Global styling
  style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

  st.title('Emissions Executive Summary')
  dfs_to_concat = []

  if 's1de_calc_results' in state and state['s1de_calc_results'] != {}:
    s1_res = state['s1de_calc_results']
    s1_df = calculators_2_df(s1_res)
    dfs_to_concat.append(s1_df)
  else:
    st.info('Calculated results of Scope 1 has yet to be retrieved. Main dashboard will not include results for Scope 1.')
    

  if 's2ie_calc_results' in state and state['s2ie_calc_results'] != {}:
    s2_res = state['s2ie_calc_results']     
    s2_df = calculators_2_df(s2_res)
    dfs_to_concat.append(s2_df)
  else:
    st.info('Calculated results of Scope 2 has yet to be retrieved. Main dashboard will not include results for Scope 2.')

  if 's3vc_calc_results' in state and state['s3vc_calc_results'] != {}:
    s3_res = state['s3vc_calc_results'] # key: Model name, val: Calculator # 
    s3_df = calculators_2_df(s3_res) # convert each k/v to df
    dfs_to_concat.append(s3_df)
  else:
    st.info('Calculated results of Scope 3 has yet to be retrieved. Main dashboard will not include results for Scope 3.')

  standardized_dfs = [standardize_scope_df(df) for df in dfs_to_concat] # category columns with high cardinal will be REMOVED 
  if standardized_dfs:
    df = pd.concat(standardized_dfs, ignore_index=True)
    df = standardize_merged_df(df)

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


    with st.expander('Show Timeseries'):
      timeseriesPart(df)


    with st.expander('Show Year-on-Year Change'):
      yoyPart(df)


    # table export
    with st.expander('Download calculation results'):
      cols = [
        'uuid', 'date', 
        'scope', 'category', 'category_name', 
        'emission_result', 'metadata'
      ]
      raw_df = pd.concat(dfs_to_concat, ignore_index=True)
      pandas_2_AgGrid(raw_df[cols], height=350)

      st.download_button(
        label='Download calculation results',
        data=convert_df(raw_df[cols]),
        file_name=f'calculation_results.csv',
        mime='text/csv'
      )



        

  else:
    st.error('No data available.')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')
    st.write(' ')



#-- PARTS --# 

def emissionOverviewPart(df):      
    with st.expander('Emissions Overview', expanded=True):
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
      temp = temp.sort_values('scope_str', ascending=True)
      total_co2e = temp['emission_result'].sum()

      # st.write(temp)

      donut_fig = make_donut_chart(
        temp, group_col='scope_str', value_col='emission_result', hole=0.5, theme='bj3', 
        center_text=f'<b>Total<br>Emissions :<br>{format_metric(total_co2e)} <b>', hover_units='kg',
        horizontal_legend=True, height=600, sort_order=False, legend_sort=False
      )
      
      c1,c2,c3 = st.columns([1,3,1])
      with c2:
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
              orientation='h',
              hovertemplate="%{value}%",
          ))

      # Update layout
      fig.update_layout(
          title='Upstream vs Downstream Emissions',
          xaxis=dict(title='Percentage'),
          yaxis=dict(title='', tickvals=[]),
          barmode='stack',
          height=250,
          template='gecko3',
          legend=dict(
            orientation='h',
            x=0.5,
            y=1,
            xanchor='center',
            yanchor='bottom',
            traceorder="normal",
          ),
          hoverlabel=dict(font_size=18),
      )

      c1,c2,c3 = st.columns([1,6,1])
      with c2:
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

      category_col = 'category_name'
      value_col='emission_result'
      unit='kg'
      grouped_df = scope_df.copy() # 
      
      if show_percent:
        total_value = grouped_df[value_col].sum()
        grouped_df[value_col] = 100 * grouped_df[value_col] / total_value
        unit='%'
      
      grouped_df = sort_str_column_numeric(grouped_df, category_col, ascending=False)
      height = 200
      nuniq = len( grouped_df[category_col].unique() )
      height += nuniq * 50
      
      fig = go.Figure()
      for cat in grouped_df[category_col].unique() if category_col else [None]:
        cat_data = grouped_df[grouped_df[category_col] == cat] if category_col else grouped_df
        sum_of_cat = cat_data[value_col].sum() # total all values for each category
        hover_template_str = f"<b>%{{label}}</b><br>%{{value:.2f}} {unit}" 

        if nuniq <= 3:
          name = str(cat) # Full name of category (EG: C9: Downstream Transport)
        else:
          # Adjust the regex to match the number following a letter and colon
          match = re.search(r'[a-zA-Z](\d+):', str(cat))
          if match:
            number_part = match.group(1)  # Get the numeric part
            name = f"C{number_part}"
          else:
            name = str(cat)

        
        fig.add_trace(go.Bar(
          y=[cat],
          x=[sum_of_cat],
          name=name,
          text=[f"<b>{cat}</b><br><b>{sum_of_cat:.2f}</b>"],
          textposition='inside',
          orientation='h',
          hovertemplate=hover_template_str,
        ))

      fig.update_layout(
        title=f'Scope {scope}',
        title_x=0.5,
        title_y=1, 
        hoverlabel=dict(font_size=18),
        height=height,
        showlegend=show_legend,
        legend=dict(orientation='h', x=0, y=0.9, xanchor='left', yanchor='top'),
        legend_traceorder="reversed",

        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        xaxis=dict(domain=[0, 1]),
        yaxis=dict(domain=[0, 0.8]),
        template='bj7_v2',
      )

      c1,c2,c3 = st.columns([1,6,1])
      with c2:
        st.plotly_chart(fig, use_container_width=True)
      st.divider()


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
      fig.update_layout(title_text="<b>Emissions Flow</b>", title_x=0.5, font_size=16, height=700)
      fig.update_layout(hoverlabel=dict(font_size=20))
      fig.update_layout(template='google')
      fig.update_layout(images=watermark(x=0.985, y=0.015, xanchor="right", yanchor="bottom"))
      fig.update_layout(showlegend=False)
      return fig
  

  with st.expander('Emissions Flow Discovery'):
    categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
    exclude_columns = {'uuid', 'date', 'category'}
    categorical_columns = list(categorical_columns - exclude_columns)

    with st.form(key='hierarchy_form'):
      initial_items = ['category_name', 'stream']
      original_items = [
          {'header': 'Available fields',  'items': [humanize_field(x) for x in categorical_columns if x not in initial_items]},
          {'header': 'Hierarchy Order', 'items': [humanize_field(x) for x in initial_items]}
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
        computerize_hierarchy_list = [humanize_field(col, invert=True) for col in hierarchy_list] # turn humanized cols back to computer str

        for col in computerize_hierarchy_list:
          temp = temp[temp[col].notna()]
          removed_rows = original_len - len(temp)
          
          if original_len > 0 and removed_rows > 0:
            if removed_rows >= original_len:
              st.error(f'Selected column {col} is incompatible for the current flowchart and will result in empty dataset.')
              original_len -= removed_rows
            else:
              st.info(f'{removed_rows} rows were removed from {original_len} during subsetting for "{humanize_field(col)}". Remaining datapoints: {original_len - removed_rows}')
              original_len -= removed_rows

        if len(temp) == 0:
          st.warning("Unable to display emission flow chart under this combination of hierarchy. Please adjust the columns.")  
        else:
          state['hierarchal_flow_df'] = temp
          state['hierarchy_list'] = computerize_hierarchy_list

    if 'hierarchal_flow_df' in state and 'hierarchy_list' in state:
      sankey_fig = make_sankey_chart(state['hierarchal_flow_df'], hierarchy_col_list=state['hierarchy_list'], value_col='emission_result')
      st.plotly_chart(sankey_fig, use_container_width=True)



def contributorAnalysisPart(df):
  with st.expander('Contributor Analysis'):
      # Get only categorical or object columns
      categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
      exclude_columns = {'uuid', 'date', 'category'}
      categorical_columns = list(categorical_columns - exclude_columns)

      # Humanize column names for display
      humanized_columns = {col: humanize_field(col) for col in categorical_columns}

      # Select category
      c1,c2 = st.columns([1,1])
      with c1:
        display_type = st.selectbox('Display mode', options=['Bar', 'Pie'], key='display_contribute')
      with c2:        
        humanized_column_names = [humanized_columns[col] for col in categorical_columns]
        default_index_category = humanized_column_names.index(humanize_field('category_name')) if 'category_name' in categorical_columns else 0
        selected_humanized_category = st.selectbox('Select category', humanized_column_names, key='selected_category_contribute', index=default_index_category)

      # Group DataFrame by selected option and sum the emission_result
      selected_category = next(key for key, value in humanized_columns.items() if value == selected_humanized_category)
      grouped_df = df.groupby(selected_category)['emission_result'].sum().reset_index()

      # Sort DataFrame by emission_result
      sorted_df = grouped_df.sort_values('emission_result', ascending=False)

      # Limit to top 10 and combine the rest as 'Others'
      top_10_df = sorted_df.head(10)
      others_sum = sorted_df.iloc[10:]['emission_result'].sum()
      others_delta = sorted_df.iloc[9]['emission_result'] - others_sum if len(sorted_df) > 10 else 0
      others_df = pd.DataFrame({f'{selected_category}': ['Others'], 'emission_result': [others_sum], 'delta': [others_delta]})
      sorted_df = pd.concat([top_10_df, others_df], ignore_index=True)
      sorted_df = sorted_df.sort_values('emission_result', ascending=False)

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
              yaxis='y1',
              hovertemplate=f"%{{value:.2f}} kg"
          ))

      # Cumulative Sum Line
      fig_v.add_trace(go.Scatter(
          x=sorted_df[selected_category],
          y=sorted_df['cum_sum_percent'],
          mode='lines+markers',
          name='Cumulative Sum (%)',
          yaxis='y2',
          hovertemplate ='%{y:.2f} %',
      ))

      # Update layout
      fig_v.update_layout(
          title='',
          xaxis_title=f'<b>{selected_humanized_category}</b>',
          yaxis=dict(title='<b>Emission Result</b>', domain=[0, 0.8]),
          yaxis2=dict(
              title='<b>Cumulative Sum (%)</b>',
              overlaying='y',
              side='right',
              range=[0, 100], 
              domain=[0, 0.8]
          ),
          height=600,
          template='google',
          legend=dict(orientation='h', x=0, y=0.9, xanchor='left', yanchor='bottom'),
          showlegend=True,
          hovermode="x",
          hoverlabel=dict(font_size=18),
          images=watermark(),
      )
      c1,c2,c3=st.columns([1,4,1])

      with c2:
        if display_type == 'Bar':
          st.plotly_chart(fig_v, use_container_width=True)
        
        else:
          # Make a truncated donut chart
          fig  = make_donut_chart(
            sorted_df, group_col=selected_category, value_col='emission_result', 
            center_text=f'<b>Total<br>Emissions :<br>{format_metric(sorted_df["emission_result"].sum())} <b>',
            hole=0.5, height=700, theme='google', horizontal_legend=True
          )
          st.plotly_chart(fig, use_container_width=True)





def dataQualityPart(df):
  with st.expander('Data Quality Report'):
    # category only
    categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
    exclude_columns = {'uuid', 'date'}
    categorical_columns = list(categorical_columns - exclude_columns)
    humanize_categorical_columns = [humanize_field(col) for col in categorical_columns]

    # numeric only
    numerical_columns = set(df.select_dtypes(include=['float']).columns)
    exclude_columns = {'data_quality', 'scope', 'category', 'state', 'country', 'lat', 'lon'}
    numerical_columns = list(numerical_columns - exclude_columns)
    humanize_numerical_columns = [humanize_field(col) for col in numerical_columns]

    # Select category
    c1,c2 = st.columns([1,1])
    with c1:
      default_index_numeric = numerical_columns.index('emission_result') if 'emission_result' in numerical_columns else 0
      selected_numeric = st.selectbox('Select Y-axis', humanize_numerical_columns, index=default_index_numeric)
    with c2:
      default_index_category = categorical_columns.index('category_name') if 'category_name' in categorical_columns else 0
      selected_category = st.selectbox('Select category', humanize_categorical_columns, key='selected_category_dq', index=default_index_category)

    temp = df.copy()
    computerize_selected_category = humanize_field(selected_category, invert=True)
    computerize_selected_numeric = humanize_field(selected_numeric, invert=True)

    # Find the top 10 most occurring categories
    top_10_categories = temp[computerize_selected_category].value_counts().nlargest(10).index.tolist()

    # Filter the DataFrame to only include the top 10 categories
    temp = temp[temp[computerize_selected_category].isin(top_10_categories)]

    min_val = np.nanmin(temp['emission_result'])
    max_val = np.nanmax(temp['emission_result'])
    temp['size'] = np.where(
      temp['emission_result'].notna(),
      (np.log(temp['emission_result'] + 1) - np.log(min_val + 1)) / (np.log(max_val + 1) - np.log(min_val + 1)),
      np.nan
    )
    temp['size'] = temp['size'].fillna(0)

    xdata = 'data_quality'
    sdata = 'emission_result'

    fig = px.scatter(
      temp, x=xdata, y=computerize_selected_numeric, color=computerize_selected_category, 
      size='size', 
      opacity=0.6
    )

    fig.update_traces(
      hovertemplate = "Data Quality: %{x}<br>Emissions: %{y:.2f} kg"
    )

    fig.update_layout(
      title='Data Gap Discovery',
      xaxis_title=f'<b>{humanize_field(xdata)}</b>',
      yaxis=dict(title=f'<b>{selected_numeric}</b>'),
      height=600,
      width=900,
      template='google',
      legend=dict(orientation='h', title=None, x=0, y=1, xanchor='left', yanchor='bottom'),
      hoverlabel=dict(font_size=20),
      images=watermark(),
    )
    fig.update_xaxes(range=[-0.5, 6])

    c1, c2,c3 = st.columns([1,4,1])
    with c2:
      st.plotly_chart(fig, use_container_width=True)




def timeseriesPart(df):
  # Get only categorical or object columns
  categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
  exclude_columns = {'uuid', 'date', 'category'}
  categorical_columns = list(categorical_columns - exclude_columns)
  humanize_categorical_columns = [humanize_field(col) for col in categorical_columns]

  c1, c2 = st.columns([1,1])
  with c1:
    selected_cat = st.selectbox('Select category', options=humanize_categorical_columns, key='ts_select_cat')
  with c2:
    selected_frequency = st.selectbox('Select frequency', options=['Monthly', 'Quarterly', 'Yearly'], key='ts_select_freq')

  # Map selected frequency to pandas offset aliases
  freq_map = {
    'Monthly': 'ME',
    'Quarterly': 'QE',
    'Yearly': 'YE'
  }

  xdata = 'date'
  ydata = 'emission_result'
  cdata = humanize_field(selected_cat, invert=True)
  freq = freq_map.get(selected_frequency, 'ME')

  temp = df.copy()
  temp['date'] = pd.to_datetime(temp['date'])  # Ensure 'date' column is datetime type

  # Group by end of month and selected category, summing emission_result
  temp = temp.groupby([pd.Grouper(key='date', freq=freq), cdata])[ydata].sum().reset_index()

  # Create a complete date range for all months/quarters/years, then create a DataFrame with all combinations of dates and categories
  all_freq = pd.date_range(start=temp['date'].min(), end=temp['date'].max(), freq=freq)
  all_cats_for_freq = pd.MultiIndex.from_product([all_freq, temp[cdata].unique()], names=['date', cdata]).to_frame(index=False)

  # Merge with filtered groupby
  temp = pd.merge(all_cats_for_freq, temp, on=['date', cdata], how='left')
  temp[ydata] = temp[ydata].fillna(0)

  # print(temp)

  fig = px.histogram(temp, x='date', y=ydata, color=cdata, barmode='overlay', template='plotly_dark')
  st.plotly_chart(fig, use_container_width=True)


def yoyPart(df):
  # Get only categorical or object columns
  categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
  exclude_columns = {'uuid', 'date', 'category'}
  categorical_columns = list(categorical_columns - exclude_columns)
  humanized_categorical_columns = [humanize_field(col) for col in categorical_columns]

  c1, c2 = st.columns([1,1])
  with c1:
    selected_cat = st.selectbox('Select category', options=humanized_categorical_columns, key='yoy_select_cat')

  ydata = 'emission_result'
  cdata = humanize_field(selected_cat, invert=True)

  # ensure 'year' column exists
  temp = df.copy()
  temp['year'] = pd.to_datetime(temp['date']).dt.year
  
  temp = temp.groupby(['year', cdata]).agg({ydata: 'sum'}).reset_index()  
  temp['yoy_change'] = temp.groupby(cdata)[ydata].pct_change() * 100  # Percentage change

  # Charting
  unique_categories = temp[cdata].unique()
  colors = px.colors.qualitative.Plotly  # Use default color palette
  color_map = {cat: colors[i % len(colors)] for i, cat in enumerate(unique_categories)}
    
  fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.8, 0.2])
    
  # Line chart for emissions
  for cat in unique_categories:
      cat_data = temp[temp[cdata] == cat].sort_values('year')
      fig.add_trace(go.Scatter(
          x=cat_data['year'],
          y=cat_data[ydata],
          mode='lines',
          name=humanize_field(cat),
          line=dict(color=color_map[cat])
      ), row=1, col=1)
  
  # Bar chart for YoY change
  for cat in unique_categories:
      cat_data = temp[temp[cdata] == cat].sort_values('year')
      fig.add_trace(go.Bar(
          x=cat_data['year'],
          y=cat_data['yoy_change'],
          name=humanize_field(cat),
          marker=dict(color=color_map[cat])
      ), row=2, col=1)
  
  fig.update_layout(
      height=700,
      title='<b>Year on Year Change</b>',
      xaxis_title='Year',
      yaxis_title='Emissions',
      barmode='group',
      showlegend=True
  )
  
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
    'uuid', 'date', 'description',
    'scope', 'category', 'category_name', 'stream',
    'emission_result', 'most_reliable_co2e', 'financed_emissions', 'emission_removals',
    'data_quality',

    # name
    'product_name', 'distributor_name', 'process_name', 'supplier_name',

    # asset status
    'ownership_status', 'ownership_share', 'asset_class', 'sector', 'is_listed', 

    # location
    'country', 'state', 'city', 'company_name', 

    # types
    'refrigerant_type', 'vehicle_type', 'freight_type', 'fuel_type', 'waste_type', 'financial_type', 
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


def watermark(x=0.8, y=0.9, sizex=0.2, sizey=0.2, opacity=0.2, xanchor='left', yanchor='bottom'):
  return [dict(
    source= Image.open("./resources/BlackText_Logo_Horizontal.png"),
    xref="paper", yref="paper",
    x=x, y=y,
    sizex=sizex, sizey=sizey, opacity=opacity,
    xanchor=xanchor, yanchor=yanchor
  )]