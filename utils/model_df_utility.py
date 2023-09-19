import streamlit as st
import pandas as pd
import numpy as np


def df_to_calculator(df:pd.DataFrame, calculator, creator, progress_bar=True):
  """ 
  df: pd.DataFrame

  calculator: 
    Calculator object. 
    Example usage: `calc.add_data( row.to_dict() )`

  creator:
    Validator function for rows. Passing `row.to_dict()` might end up creating a Model object that is incompatible to the calculator. 
    Example: `create_data_for_model(**kwargs) -> Model(**kwargs)`. Advised to use `partial(create_data)` as input param. 
  """
  df = df.replace('<Blank>', None)
  df = df.replace(np.nan, None)

  if progress_bar:
    progress_bar = st.progress(0)
    nrows = len(df)

  warning_messages = []
  for idx, row in df.iterrows():
    try:
      data = creator(row=row) # make sure your creator must have 'row' as parameter
      calculator.add_data(data) # calculator must have internal function 'add_data()'
    except Exception as e:
      warning_messages.append(f'Unable to add data for row {idx+1}. Traceback: {e}')
      pass
    
    if progress_bar:
      progress_pct = (idx+1) / nrows
      progress_bar.progress(progress_pct)

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


