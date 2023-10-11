import re

#--- Lookup ---#
GWP_DICT = {
    'CO2': 1,
    'CH4': 25,
    'N2O': 198
}


def get_relevant_factors(factors, unit:str):
    """
    factors:
        dict containing keys for CO2, CH4, N2O, ...
    unit: 
        the suffix for column EG: _kwh, _mton, _litre

    Returns:
        key value pair for each chemical and factor value
    """
    try:
        relevant_factors = {}
        chemicals = ['co2', 'ch4', 'n2o'] # expand when needed

        # Retrieve all columns with the specified fuel_unit in it
        for key, value in factors.items():
            if re.search(f'_{unit}', key, re.IGNORECASE):

                # Retrieve all remaining columns containing chemicals
                for chem in chemicals:
                    if re.search(chem, key, re.IGNORECASE):
                        chemical_name = key
                        relevant_factors[chemical_name] = value
                        break           
        return relevant_factors
    
    except Exception as e:
        print(f"Unable to retrive relevant factors from {factors}. Error: {e}")
        return {}


def calculate_co2e(relevant_factors:dict, unit_value:float, unit_of_interest:str=None, gwp:dict=None):
    """ 
    Input Parameters

    relevant_factors:
        Example 1: {'kgCO2_unit': 0.014384, 'gCH4_unit': 0.001096, 'gN2O_unit': 0.000342}
        Example 2: {'kgCO2_m3': 1.9225, 'gCH4_m3': 0.0364, 'gN2O_m3': 0.0035}

    gwp:
        Dict containing global warming potentials for different gas.
        Key = chemical name, value = CO2 multiplier

    unit_value:
        Value to multiply each GHG

    unit_of_interest:
        String name suffix to refer to the correct GHG factors from provided "relevant_factors". 
    """
    total_co2e = 0
    
    # use default GWP table if not provided
    if not gwp:
        gwp = GWP_DICT
        
    if not relevant_factors:
        print('Unable to calculate co2e, no relevant factors provided')
        return total_co2e
    
    for full_key, factor in relevant_factors.items():
        if not isinstance(factor, (int, float)):
            continue

        # Match fields with chemical
        chemical_match = re.search(r'(?i)(CO2|CH4|N2O)', full_key)
        if not chemical_match:
            continue
            
        # Match remainder fields with unit
        unit_match = re.search(r'_(\w+)$', full_key)
        if not unit_match:
            continue  
            
        # Check if the unit matches the unit of interest
        if unit_of_interest and unit_match.group(1) != unit_of_interest:
            continue

        ghg_type = chemical_match.group(0).upper()
        gwp_value = gwp.get(ghg_type, 1)  # Default to 1 if not found
        
        # WARNING: hard coded multipliers
        # work around for n2o, ch4 represented as g not kg in db
        if ghg_type in ['N2O', 'CH4']:
            mass_multiplier = 1e-3
        else:
            mass_multiplier = 1

        # Calculate the emission value
        emission_value = unit_value * factor * mass_multiplier
        total_co2e += emission_value * gwp_value

    return total_co2e


