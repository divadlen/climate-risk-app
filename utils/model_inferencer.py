import pandas as pd
import numpy as np
from collections import Counter

from utils.s3vc_Misc.s3_models import *
from utils.s3vc_Misc.s3c15_models import *


class ModelInferencer:
    def __init__(self):
        self.available_models = {
            # Non C15
            'S3C1_PurchasedGoods': S3C1_PurchasedGoods,
            'S3C2_CapitalGoods': S3C2_CapitalGoods,
            'S3C3_EnergyRelated': S3C3_EnergyRelated,
            'S3C4_UpstreamTransport': S3C4_UpstreamTransport,
            'S3C5_WasteGenerated': S3C5_WasteGenerated,
            
            'S3C6_1_BusinessTravel': S3C6_1_BusinessTravel,
            'S3C6_2_BusinessStay': S3C6_2_BusinessStay,
            
            'S3C7_EmployeeCommute': S3C7_EmployeeCommute,
          
            'S3C8_1_UpstreamLeasedEstate': S3C8_1_UpstreamLeasedEstate,
            'S3C8_2_UpstreamLeasedAuto': S3C8_2_UpstreamLeasedAuto,

            'S3C9_DownstreamTransport': S3C9_DownstreamTransport,
            'S3C10_ProcessingProducts': S3C10_ProcessingProducts,
            'S3C11_UseOfSold': S3C11_UseOfSold,
            'S3C12_EOLTreatment': S3C12_EOLTreatment,

            'S3C13_1_DownstreamLeasedEstate': S3C13_1_DownstreamLeasedEstate,
            'S3C13_2_DownstreamLeasedAuto': S3C13_2_DownstreamLeasedAuto,             
            
            'S3C14_Franchise': S3C14_Franchise,

            # C15 
            'S3C15_BaseAsset': S3C15_BaseAsset,
            'S3C15_1A_ListedEquity': S3C15_1A_ListedEquity,
            'S3C15_1B_UnlistedEquity': S3C15_1B_UnlistedEquity,
            'S3C15_1C_CorporateBonds': S3C15_1C_CorporateBonds,
            'S3C15_1D_BusinessLoans': S3C15_1D_BusinessLoans,
            'S3C15_1E_CommercialRealEstate': S3C15_1E_CommercialRealEstate,
            'S3C15_2A_Mortgage': S3C15_2A_Mortgage,
            'S3C15_2B_VehicleLoans': S3C15_2B_VehicleLoans,
            'S3C15_3_ProjectFinance': S3C15_3_ProjectFinance,
            'S3C15_4_EmissionRemovals': S3C15_4_EmissionRemovals,
            'S3C15_5_SovereignDebt': S3C15_5_SovereignDebt,
        }
        self.model_instances = {key: [] for key in self.available_models.keys()}

    def infer_model_from_df(self, df: pd.DataFrame):
        scores = {}
        df_columns = set(df.columns)

        for name, Model in self.available_models.items():
            all_fields = set(Model.model_fields.keys()) # model fields
            model_coverage = len(all_fields.intersection(df_columns)) / len(all_fields) if len(all_fields) != 0 else 0 # Check coverage of BaseModel by df
            df_coverage = len(df_columns.intersection(all_fields)) / len(df_columns) if len(df_columns) != 0 else 0 # Check coverage of df by BaseModel

            score = model_coverage ** 2 + df_coverage ** 2            
            scores[name] = score
            
        highest_score = max(scores.values())
        best_fit_models =  [{"model": model, "score": score} for model, score in scores.items() if score == highest_score]

        # Some models have identical fields, but different default values
        if len(best_fit_models) > 1:
            for bfm in best_fit_models:
                name = bfm['model']
                Model = self.available_models[name]
                tiebreaker = 0
                
                # search for model fields and get default values
                for field, field_info in Model.model_fields.items():
                    if field in df.columns:
                        default_value = field_info.default
                        
                        # Rank only legit defaults
                        if default_value not in ['None', 'PydanticUndefined']:
                            value_counts = Counter(df[field])
                            tiebreaker += value_counts.get(default_value, 0)
                
                bfm['tiebreaker'] = tiebreaker
            best_fit_models.sort(key=lambda x:x['tiebreaker'], reverse=True)
                
        if best_fit_models[0]['score'] > 1:
            return best_fit_models[0]
        
        print(f'Dataframe contains only low probability matches. Score: {best_fit_models[0]["score"]}')
        return None

    def transform_df_to_model(self, df: pd.DataFrame): 
        """ 
        Turns all rows in df into filled models. NO PROTECTION AGAINST DUPLICATE ENTRIES!
        """
        try:  
            model_name = self.infer_model_from_df(df)['model']
        except:
            model_name = None

        if model_name:
            print(f'Discovered model {model_name}! Appending rows as model fields...\n')
            Model = self.available_models[model_name]
            
            df = df.copy()
            df = df.replace('<Blank>', None)
            df = df.replace(np.nan, None)
            
            for idx, row in df.iterrows():
                try:
                    instance = Model(**row.to_dict())
                    self.model_instances[model_name].append(instance)
                
                    print(f'Row {idx+1} appended!')
                    print(f'Model={model_name}')
                    print(f'Content={row.to_dict()}\n')
                    
                except Exception as e:
                    print(f'Failed to append row {idx+1}! Model={model_name}, {e}\n')