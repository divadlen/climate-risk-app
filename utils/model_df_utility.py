import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import traceback


def df_to_calculator(df:pd.DataFrame, calculator, creator, progress_bar=True, return_invalid_indices=False):
  """ 
  Args:
  df (pd.DataFrame): 
    The DataFrame to process.
  
  calculator: 
    Calculator object. 
    Example usage: `calc.add_data( row.to_dict() )`
    
  creator:
    Validator function for rows. Passing `row.to_dict()` might end up creating a Model object that is incompatible to the calculator. 
    Example: `create_data_for_model(**kwargs) -> Model(**kwargs)`. Advised to use `partial(create_data)` as input param. 
    
  progress_bar (bool): 
    Whether to show a progress bar (default is True).
  
  return_invalid_indices (bool): 
    Whether to return indices of invalid rows (default is False).

  Returns:
    tuple: A tuple containing the calculator, warning messages, and optionally invalid row indices.
  """
  df = df.replace('<Blank>', None)
  df = df.replace('<To fill>', None)
  df = df.replace(np.nan, None)

  if progress_bar:
    progress_bar = st.progress(0)
    nrows = len(df)

  warning_messages = []
  invalid_rows = set()  # Track indices of invalid rows
  for idx, row in df.iterrows():
    try:
      data = creator(row=row) # make sure your creator must have 'row' as parameter
      calculator.add_data(data) # calculator must have internal function 'add_data()'

    except Exception as e:
      warning_messages.append(f'Unable to add data for row {idx+1}. Traceback: {e}') # idx + 1 because python idx starts from 0
      invalid_rows.add(idx) 
      traceback.print_exc()
      pass
    
    if progress_bar:
      progress_pct = (idx+1) / nrows
      progress_bar.progress(progress_pct)

  if return_invalid_indices:
    return calculator, warning_messages, invalid_rows
  else:
    return calculator, warning_messages


def calculator_to_df(calculator):
    """ 
    calculator: 
      Example: S2IE_Calculator, S1MC_Calculator
      Calc output is expected to be built like this >> self.calculated_emissions[key] = {'input_data': ppd, 'calculated_emissions': calculated_emissions}
    """
    data = []
    
    for emission in calculator.calculated_emissions.values(): # calculator class must have 'calculated_emissions' attribute
        model_data = None
        emission_data = None
        
        for key, value in emission.items():
            if 'emissions' in key.lower():
                emission_data = value.model_dump() if hasattr(value, 'model_dump') else value
            else:
                model_data = value.model_dump() if hasattr(value, 'model_dump') else value
        
        if model_data is not None and emission_data is not None:
            combined_data = {**model_data, **emission_data}
            data.append(combined_data)
    
    return pd.DataFrame(data)


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
          # row[k] = v

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