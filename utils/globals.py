LOCATION_ABBRV = {
  'usa': 'United States of America',
  'united states': 'united of america',
  'uk': 'United Kingdom',
  'korea': 'south korea',
  'my': 'malaysia',
  'melaka': 'malacca',
  'pineng': 'Penang',
}

COLUMN_SORT_ORDER = [
  # Universal
  'uuid', 'date', 'description',
  'employee_id', 'franchisee_id', 'customer_id',
  'product_name', 'product_class',
  'distributor_name', 'customer_name',
  'process_name',
  'equipment_name',
  'asset_name',

  # counter
  'lifetime_usage_freq', 'number_sold', 
  'no_of_nights', 
  'frequency', 'sampled_days',

  # asset status
  'leased_asset_name', 'leased_asset_type', 'ownership_status', 'ownership_share',

  # location
  'lat', 'lon',  
  'country_code', 'country', 'state',
  'address', 'address_from', 'address_to', 
  'branch', 'department', 'street_address_1', 'street_address_2', 'city', 'postcode',

  # Company descriptions
  'financial_type', 'company_name', 'asset_class',
  'sector', 'subsector', 
  'is_listed', 'owned', 
  'date_acquired', 'date_disposed',

   # supplier descriptions
  'supplier_name', 'purchased_quantity', 'quantity_unit', 'quantity_emission_factor', 'supplier_incurred_emissions',

  # vehicle descriptions
  'travel_mode', 'vehicle_type', 'vehicle_value',

  # freight descriptions
  'freight_type', 'freight_weight',

  # fuel descriptions
  'fuel_state', 'fuel_type', 'fuel_unit', 
  'fuel_use', 'fuel_per_use', 'fuel_consumption',  
  'heating_value', 'fuel_spend',

  # energy descriptions
  'energy_provider', 'energy_type', 'energy_unit', 
  'energy_use', 'energy_per_use', 'energy_consumption', 
  'energy_spend',

  # electric descriptions
  'electric_use', 'electric_per_use', 
  'grid_emission_factor',

  # refrigerant descriptions
  'refrigerant_type', 'refrigerant_unit',
  'refrigerant_use', 'refrigerant_per_use',
  'refrigerant_capacity',

  # distance descriptions
  'distance_traveled', 'distance', 'distance_unit', 
  'distance_cadence', 'distance_emission_factor', 

  # building descriptions
  'floor_area', 'area_unit', 'building_energy_use', 'building_emission_factor', 'year_constructed', 'property_value',

  # waste descriptions
  'waste_type', 'waste_quantity', 'waste_state', 'waste_unit', 'waste_treatment_method', 'waste_treatment_provider',

  # finances
  'currency', 'outstanding_amount', 'enterprise_value', 'total_equity', 'total_debt', 
  'project_equity', 'project_debt',
  'total_government_debt', 'PPP_adj_GDP', 
  'value_at_origin', 

  # emission related
  'attribution_share', 'reported_emissions', 'project_emissions', 'emissions_removed', 'production_emissions', 'consumption_emissions', 'estimated_emissions', 'emission_estimation_description',
  'upstream_emission_factor', 'life_cycle_emission_factor', 'combustion_emission_factor', 'energy_loss_rate',
  'hotel_emission_factor',

  # refrigerant related
  'install_loss_rate', 'annual_leak_rate', 'recovery_rate', 
  'number_of_year',
]


#--- USED BY S3VC --#
SUPPORTED_FINANCIAL_TYPE = [
  'Corporate Finance', 'Consumer Finance', 'Consumer Finance'
]

SUPPORTED_ASSET_CLASS = [
  'Corporate Bonds', 'Listed Equity', 'Unlisted Equity', 'Business Loans', 'Commercial Real Estate', 
  'Mortgage', 'Vehicle Loan',
  'Emission Removal', 'Sovereign Debt',
]

# Mapping sectors to applicable categories by index
SECTOR_TO_CATEGORY_IDX = {
  'Energy': [1, 4, 9, 11],
  'Industrial': [1, 3, 4, 5, 6, 7, 9, 10, 11],
  'Construction': [1, 3, 4, 5, 6, 7, 9, 10, 11],
  'Telecommunication': [5, 6, 7, 9],
  'Transportation': [3, 5, 6, 7],
  'Automobile': [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12],
  'Real Estate': [5, 6, 7, 13],
  'Banking and Finance': [6, 7, 15],
}

IDX_TO_CATEGORY_NAME = {
  1: 'Category 1 : Purchased goods & services',
  2: 'Category 2 : Capital goods',
  3: 'Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)',
  4: 'Category 4 : Upstream transportation & distribution',
  5: 'Category 5 : Waste generated in operations',
  6: 'Category 6 : Business and air travel',
  7: 'Category 7 : Employee commuting',
  8: 'Category 8 : Upstream leased assets',
  9: 'Category 9 : Downstream distribution of sold products',
  10: 'Category 10 : Processing of sold products',
  11: 'Category 11 : Use of sold products',
  12: 'Category 12 : End-of-life treatment of sold products',
  13: 'Category 13 : Downstream leased assets',
  14: 'Category 14 : Franchises',
  15: 'Category 15 : Investments',
}

ABBRV_IDX_TO_CATEGORY_NAME = {
  'S3C1': 'Category 1 : Purchased goods & services',
  'S3C2': 'Category 2 : Capital goods',
  'S3C3': 'Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)',
  'S3C4': 'Category 4 : Upstream transportation & distribution',
  'S3C5': 'Category 5 : Waste generated in operations',
  
  'S3C6_1': 'Category 6.1 : Business and air travel',
  'S3C6_2': 'Category 6.2 : Business trips and stays',
  
  'S3C7': 'Category 7 : Employee commuting',

  'S3C8_1': 'Category 8.1 : Upstream leased estate',
  'S3C8_2': 'Category 8.2 : Upstream leased automobiles & machinery',

  'S3C9': 'Category 9 : Downstream distribution of sold products',
  'S3C10': 'Category 10 : Processing of sold products',
  'S3C11': 'Category 11 : Use of sold products',
  'S3C12': 'Category 12 : End-of-life treatment of sold products',
  
  'S3C13_1': 'Category 13.1 : Downstream leased estate',
  'S3C13_2': 'Category 13.2 : Downstream leased automobiles & machinery',
  
  'S3C14': 'Category 14 : Franchises',
  
  'S3C15_1A': 'Category 15.1A : Listed Equity',
  'S3C15_1B': 'Category 15.1B : Unlisted Equity', 
  'S3C15_1C': 'Category 15.1C : Corporate Bonds',
  'S3C15_1D': 'Category 15.1D : Business Loans',
  'S3C15_1E': 'Category 15.1E : Commercial Real Estate',
  'S3C15_2A': 'Category 15.2A : Mortgage',
  'S3C15_2B': 'Category 15.2B : Vehicle Loans',
  'S3C15_3': 'Category 15.3 : Project Finance',
  'S3C15_4': 'Category 15.4 : Emission Removals',
  'S3C15_5': 'Category 15.5 : Sovereign Debt',
  'S3C15_6': 'Category 15.6 : Managed Investments',
}



class ColorDiscrete:
  tableau = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
  colorbrewer = ['#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33', '#A65628', '#F781BF', '#999999']
  google = ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722'] 
  d3 = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF']
  ilo = ['#0094D2', '#E6007E', '#F47D30', '#212121', '#F0F0F0'] 
  okabe_ito = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7', '#000000', '#F0E442', '#D55E00']
  economist = ['#E3120B', '#4C4C4C', '#6D6E71', '#8E8D8F', '#AAAAB2', '#B6B4B5', '#C1BDBA', '#C9C5B6', '#D2CDC2', '#D9D5CD']
  mckinsey = ['#4A90E2', '#F5A623', '#7ED321', '#D0021B', '#417505', '#BD10E0', '#50E3C2', '#F8E71C', '#F78B00', '#000000']
  deloitte = ['#00A5DC', '#49276D', '#8A0000', '#007681', '#9A7227', '#84BE41', '#7C7474', '#D12F2F', '#F8931D', '#000000']
  nhk_jp = ['#E60012', '#579D1C', '#4B1E66', '#1B255E', '#1E4896', '#00A0E9', '#009944', '#6CBB5A', '#D1C000', '#E39800']
  abc_aus = ['#E14100', '#008C45', '#00AEEF', '#7600A1', '#80C342', '#005BB5', '#93C6E0', '#F15A29', '#DF7C00', '#00B5E2']

  bj3 = ['#004457', '#db8b00', '#570044']
  bj7 = ['#5555cb','#978cd7','#a6a6a6','#6f6f6f','#b2a9dc','#d6d6d6','#30309c']
  bj7_v2 = ['#916081','#570044','#6f6f6f','#a1a1a1','#c9b7c3','#d6d6d6','#ad8ba1']

  gecko7 = ['#004457', '#567583', '#9baab1', '#B5C0CB', '#b8e8e3', '#83ede3', '#05f1e3']
  gecko5 = ['#004457', '#798f9a', '#B5C0CB', '#a0ebe3', '#05f1e3']
  gecko3 = ["#004457", "#4F8CBD", "#05eaf1"]

  gecko_v1 = [
    '#00989d', '#ffa500', 
    '#757D8e', 
    '#00b800', '#7fe67f', 
    '#e06666', '#674ea7', 
    '#b4a7d6',
   ]

  gecko_v2 = [
    '#07657F', '#4AA3B3', # blue
    '#1EA66D', '#71C4A0', # green
    '#D85252', '#E79797', # red
    '#EB9A04', '#E6CC84', # yellow
    '#553269', '#926BB2'  # purple
  ]
