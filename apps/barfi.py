import streamlit as st
from barfi import st_barfi, Block, barfi_schemas

import numpy as np
import pandas as pd
import csv
import os

from faker import Faker
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest

def barfiPage():
  uploaded_files = st.file_uploader("Choose a CSV files", type="csv", accept_multiple_files=True)
  files = []
  if uploaded_files:
    for file in uploaded_files:
      # file = pd.read_csv(file)
      files.append(file)
  else:
    files = None

  #---Select file---#
  select_file_block = Block(name='Select File')
  select_file_block.add_option(name='display-option', type='display', value='Select the file to load data.')

  if uploaded_files:
    select_file_block.add_option(name='select-file', type='select', items=uploaded_files, value=uploaded_files[0])
  else:
    select_file_block.add_option(name='select-file', type='select', items=['resources/s1sc_gas.csv'])
  
  select_file_block.add_output(name='File Data')
  def select_file_block_func(self):
    file_path = self.get_option(name='select-file')   
    df = pd.read_csv(file_path)
    self.set_interface(name='File Data', value=df)
  select_file_block.add_compute(select_file_block_func)

  #---Append a new column---#
  add_column_block = Block(name='Insert column')
  add_column_block.add_input(name='Input Dataframe 2')
  add_column_block.add_output(name='Inserted new column')
  def add_column_func(self):
      data = self.get_interface(name='Input Dataframe 2').copy() 
      data['new_column'] = 'new_value'
      self.set_interface(name='Inserted new column', value=data)
  add_column_block.add_compute(add_column_func)

  #---Insert new row---#
  add_row_block = Block(name='Insert row')
  add_row_block.add_input(name='Input Dataframe')
  add_row_block.add_output(name='Inserted new row')
  def add_row_func(self):
    data = self.get_interface(name='Input Dataframe').copy()
    new_row_index = len(data)
    data.loc[new_row_index] = np.nan
    self.set_interface(name='Inserted new row', value=data)
  add_row_block.add_compute(add_row_func)


  #---Display graph---#
  base_blocks = [select_file_block, add_row_block, add_column_block]
  barfi_schema_name = st.selectbox('Select a saved schema to load:', barfi_schemas())

  compute_engine = st.checkbox('Activate barfi compute engine', value=False)
  barfi_result = st_barfi(base_blocks=base_blocks, compute_engine=compute_engine, load_schema=barfi_schema_name)

  if compute_engine and barfi_result:
    for block_name, block_data in barfi_result.items():
      with st.expander(f"Results for {block_name}:"):
        for interface_name, interface_data in block_data['block']._outputs.items():
          value = block_data['block'].get_interface(name=interface_name)
          st.write(f'{interface_name} :')
          st.write(value) 
  
  elif barfi_result:
    st.write(barfi_result)




# def barfiPage():
#   st.title("Breast Cancer Patients Simulation")

#   p1block = Block(name="print1")
#   p1block.add_output()
#   p1block.add_compute(print1)

#   # Block 1: Generate Synthetic Data
#   generate_data_block = Block(name='Generate Data')
#   generate_data_block.add_output()
#   generate_data_block.add_compute(generate_data)


#   # Block 2: Preprocessing Step 1 (e.g., Encoding Categorical Features)
#   preprocessing_step1_block = Block(name='Preprocessing Step 1')
#   preprocessing_step1_block.add_input()
#   preprocessing_step1_block.add_output()
#   preprocessing_step1_block.add_compute(preprocess_step1)

#   # Block 3: Preprocessing Step 2 (e.g., Scaling Numeric Features)
#   preprocessing_step2_block = Block(name='Preprocessing Step 2')
#   preprocessing_step2_block.add_input()
#   preprocessing_step2_block.add_output()
#   preprocessing_step2_block.add_compute(preprocess_step2)

#   # Block 4: Preprocessing Step 3 (e.g., Handling Missing Values)
#   preprocessing_step3_block = Block(name='Preprocessing Step 3')
#   preprocessing_step3_block.add_input()
#   preprocessing_step3_block.add_output()
#   preprocessing_step3_block.add_compute(preprocess_step3)

#   # Block 5: Predict Survival Rate
#   predict_survival_block = Block(name='Predict Survival Rate')
#   predict_survival_block.add_input()
#   predict_survival_block.add_output()
#   predict_survival_block.add_compute(predict_survival)


#   # Block 6: Rank Feature Importance
#   rank_feature_importance_block = Block(name='Rank Feature Importance')
#   rank_feature_importance_block.add_input()
#   rank_feature_importance_block.add_output()
#   rank_feature_importance_block.add_compute(rank_feature_importance)


#   load_schema = st.selectbox('Select a saved schema:', barfi_schemas())
#   compute_engine = st.checkbox('Activate barfi compute engine', value=False)
#   # Display the Barfi interface
#   barfi_result = st_barfi(
#     base_blocks=[
#       p1block,
#       generate_data_block,
#       preprocessing_step1_block,
#       preprocessing_step2_block,
#       preprocessing_step3_block,
#       predict_survival_block,
#       rank_feature_importance_block
#     ],
#     compute_engine=compute_engine, 
#     load_schema=load_schema
#   )

#   if barfi_result:
#     st.write(barfi_result)

#   st.write(print1()) # 

#   # Display the results
#   # abc = generate_data_block._on_compute()
#   # st.write("Predictions:", abc)
#   # # st.write("Feature Importance:", feature_importance)



# # Block 1: Generate Synthetic Data
# def print1():
#     return 1

# def generate_data():
#     fake = Faker()
#     data = []
#     for _ in range(1000):
#         patient = {
#             'gender': fake.random_element(elements=('Male', 'Female')),
#             'age_group': fake.random_element(elements=('18-30', '31-50', '51-70', '71+')),
#             'treatment': fake.random_element(elements=('Surgery', 'Chemotherapy', 'Radiation')),
#             'tumor_size': fake.random_number(digits=2),
#             'lymph_nodes': fake.random_number(digits=2),
#             'metastasis': fake.random_number(digits=1),
#             'survive': fake.random_element(elements=(True, False))
#         }
#         data.append(patient)
#     return pd.DataFrame(data)

# # Block 2: Preprocessing Step 1 (Encoding Categorical Features)
# def preprocess_step1(df):
#     encoder = OneHotEncoder()
#     categorical_features = ['gender', 'age_group', 'treatment']
#     encoded_features = encoder.fit_transform(df[categorical_features]).toarray()
#     encoded_df = pd.DataFrame(encoded_features, columns=encoder.get_feature_names_out(categorical_features))
#     return pd.concat([df.drop(categorical_features, axis=1), encoded_df], axis=1)

# # Block 3: Preprocessing Step 2 (Scaling Numeric Features)
# def preprocess_step2(df):
#     scaler = StandardScaler()
#     numeric_features = ['tumor_size', 'lymph_nodes', 'metastasis']
#     df[numeric_features] = scaler.fit_transform(df[numeric_features])
#     return df

# # Block 4: Preprocessing Step 3 (Handling Missing Values)
# def preprocess_step3(df):
#     imputer = SimpleImputer(strategy='mean')
#     return pd.DataFrame(imputer.fit_transform(df), columns=df.columns)

# # Block 5: Predict Survival Rate
# def predict_survival(df):
#     X = df.drop('survive', axis=1)
#     y = df['survive']
#     model = RandomForestClassifier()
#     model.fit(X, y)
#     predictions = model.predict(X)
#     return predictions

# # Block 6: Rank Feature Importance
# # def rank_feature_importance(df, model):
# #     importances = model.feature_importances_
# #     return sorted(zip(importances, df.columns), reverse=True)

# def rank_feature_importance(df):
#     X = df.drop('survive', axis=1)
#     y = df['survive']
#     selector = SelectKBest(k=3)
#     selector.fit(X, y)
#     return selector.scores_