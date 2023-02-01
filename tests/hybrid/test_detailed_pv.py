from pathlib import Path
import pytest
from pytest import approx
import json
from hybrid.sites import SiteInfo, flatirons_site
from hybrid.layout.detailed_pv_config import *
from hybrid.layout.detailed_pv_layout import DetailedPVParameters
from hybrid.layout.hybrid_layout import PVGridParameters
from hybrid.layout.pv_module import *
from hybrid.detailed_pv_plant import DetailedPVPlant, Pvsam
from hybrid.financial.custom_financial_model import *
from hybrid.financial.custom_cost_model import CustomCostModel, BOS_DetailedPVPlant_input_map
from hybrid.hybrid_simulation import HybridSimulation

@pytest.fixture
def site():
    filepath = Path(__file__).absolute().parent / "layout_example.kml"
    site_data = {'kml_file': filepath}
    solar_resource_file = Path(__file__).absolute().parent.parent.parent / "resource_files" / "solar" / "35.2018863_-101.945027_psmv3_60_2012.csv"
    wind_resource_file = Path(__file__).absolute().parent.parent.parent / "resource_files" / "wind" / "35.2018863_-101.945027_windtoolkit_2012_60min_80m_100m.srw"
    return SiteInfo(site_data, solar_resource_file=solar_resource_file, wind_resource_file=wind_resource_file)


default_layout_config = {
    'module_power': module_power,
    'module_width': module_width,
    'module_height': module_height,
    'subarray1_nmodx': 12,
    'subarray1_nmody': 2,
    'subarray1_track_mode': 1,
    'nb_inputs_inverter': 10,
    'interrack_spac': 1,
    'perimetral_road': False,
    'setback_distance': 10,
    }

default_fin_config = {
    'batt_replacement_schedule_percent': [0],
    'batt_bank_replacement': [0],
    'batt_replacement_option': 0,
    'om_fixed': 1,
    'om_production': [2],
    'om_capacity': 0,
    'om_batt_fixed_cost': 0,
    'om_batt_variable_cost': [0],
    'om_batt_capacity_cost': 0,
    'om_batt_replacement_cost': 0,
    'system_use_lifetime_output': 0,
    'ptc_fed_amount': [0],
    'ptc_fed_escal': 0,
    'itc_fed_amount': [0],
    'itc_fed_percent': [26],
    'depr_alloc_macrs_5_percent': 90,
    'depr_alloc_macrs_15_percent': 1.5,
    'depr_alloc_sl_5_percent': 0,
    'depr_alloc_sl_15_percent': 2.5,
    'depr_alloc_sl_20_percent': 3,
    'depr_alloc_sl_39_percent': 0,
    'depr_alloc_custom_percent': 0,
    'depr_bonus_fed_macrs_5': 1,
    'depr_bonus_sta_macrs_5': 1,
    'depr_itc_fed_macrs_5': 1,
    'depr_itc_sta_macrs_5': 1,
    'depr_bonus_fed_macrs_15': 1,
    'depr_bonus_sta_macrs_15': 1,
    'depr_itc_fed_macrs_15': 0,
    'depr_itc_sta_macrs_15': 0,
    'depr_bonus_fed_sl_5': 0,
    'depr_bonus_sta_sl_5': 0,
    'depr_itc_fed_sl_5': 0,
    'depr_itc_sta_sl_5': 0,
    'depr_bonus_fed_sl_15': 0,
    'depr_bonus_sta_sl_15': 0,
    'depr_itc_fed_sl_15': 0,
    'depr_itc_sta_sl_15': 0,
    'depr_bonus_fed_sl_20': 0,
    'depr_bonus_sta_sl_20': 0,
    'depr_itc_fed_sl_20': 0,
    'depr_itc_sta_sl_20': 0,
    'depr_bonus_fed_sl_39': 0,
    'depr_bonus_sta_sl_39': 0,
    'depr_itc_fed_sl_39': 0,
    'depr_itc_sta_sl_39': 0,
    'depr_bonus_fed_custom': 0,
    'depr_bonus_sta_custom': 0,
    'depr_itc_fed_custom': 0,
    'depr_itc_sta_custom': 0,
}

default_bos_config = {

}

def test_config_verify():
    layout_conf = PVLayoutConfig(**default_layout_config)
    for k, _ in layout_conf.items():
        assert layout_conf[k] == default_layout_config[k]
    print(layout_conf)


def test_fin_construct():
    fin_model = CustomFinancialModel(Pvsam.new(), default_fin_config)
    assert fin_model.BatterySystem.batt_replacement_option == default_fin_config['batt_replacement_option']
    assert fin_model.SystemCosts.om_fixed == default_fin_config['om_fixed']
    for k, v in default_fin_config.items():
        assert fin_model.value(k) == v

def test_load_data(site):
    pvsamv1_defaults_file = Path(__file__).absolute().parent / "pvsamv1_basic_params.json"
    with open(pvsamv1_defaults_file, 'r') as f:
        tech_config = json.load(f)

    design_vec = DetailedPVParameters(
        x_position=0.25,
        y_position=0.5,
        aspect_power=0,
        s_buffer=0.1,
        x_buffer=0.1,
        gcr=0.3,
        azimuth=180,
        tilt_tracker_angle=0,
        string_voltage_ratio=0.5,
        dc_ac_ratio=1.2)

    pv_config = {
        'tech_config': tech_config,
        'layout_params': design_vec,
        'layout_config': default_layout_config,
        'fin_config': default_fin_config,
        'pan_file': "",
        'ond_file': "",
    }

    pv_plant = DetailedPVPlant(site=site, pv_config=pv_config)

    pv_plant.simulate_power(1, False)

    assert pv_plant._system_model.Outputs.annual_energy == approx(79520321.8, 1e-2)
    assert pv_plant._system_model.Outputs.capacity_factor == approx(18.15, 1e-2)

    bos_data = pv_plant.export_BOQ(BOS_DetailedPVPlant_input_map)

    # since the Cost Model depends on the whole hybrid system (shared infrastructure, land, roads, etc),
    # this step is normally called from HybridSimulation::simulate as calculate_installed_cost
    # however, for this example, we will do this manually to show how the data is passed in and out of the BOS model
    cost_model = CustomCostModel(default_bos_config) 
    pv_plant.total_installed_cost = cost_model.calculate_total_costs(bos_data)

    pv_plant.simulate_financials(5000, 1)       # TODO: implement a simple NPV calculator as an example

    pv_plant.export_financials()
    
    new_pv_design_vector = {
        'system_capacity_kw': 5000,
        'layout_params': DetailedPVParameters(
            x_position=0.5,
            y_position=0.5,
            aspect_power=0,
            s_buffer=0.1,
            x_buffer=0.1,
            gcr=0.7,
            azimuth=180,
            tilt_tracker_angle=45,
            string_voltage_ratio=0.4,
            dc_ac_ratio=1.3)
        }

    pv_plant._layout.set_layout_params(
        new_pv_design_vector['system_capacity_kw'],
        new_pv_design_vector['layout_params']
        )

    # Simulate again to ensure layout changes propagate
    pv_plant.simulate_power(1, False)

    assert pv_plant._system_model.Outputs.annual_energy == approx(9445701.25731733, 1e-1)
    assert pv_plant._system_model.Outputs.capacity_factor == approx(21.57259825712787, 1e-1)


def test_hybrid_pv_plants(site):
    pvsamv1_defaults_file = Path(__file__).absolute().parent / "pvsamv1_basic_params.json"
    with open(pvsamv1_defaults_file, 'r') as f:
        tech_config = json.load(f)

    design_vec = DetailedPVParameters(
        x_position=0.25,
        y_position=0.5,
        aspect_power=0,
        s_buffer=0.1,
        x_buffer=0.1,
        gcr=0.3,
        azimuth=180,
        tilt_tracker_angle=0,
        string_voltage_ratio=0.5,
        dc_ac_ratio=1.2)

    pv_config = {
        'tech_config': tech_config,
        'layout_params': design_vec,
        'layout_config': default_layout_config,
        'fin_config': default_fin_config,
        'pan_file': "",
        'ond_file': "",
    }

    annual_energy_expected = 79520321.8

    # Test standalone DetailedPVPlant 
    pv_plant = DetailedPVPlant(site=site, pv_config=pv_config)
    pv_plant.simulate_power(1, False)
    assert pv_plant._system_model.Outputs.annual_energy == approx(annual_energy_expected, 1e-2)
    assert pv_plant._system_model.Outputs.capacity_factor == approx(18.15, 1e-2)

    # Test DetailedPVPlant run in a hybrid simulation
    power_sources = {
        'pv': pv_config
    }
    hybrid_plant = HybridSimulation(
        power_sources,
        site,
        interconnect_kw=150e3,
        simulation_options={'pv': {'skip_financial': True}}
        )
    hybrid_plant.simulate()
    aeps = hybrid_plant.annual_energies
    assert aeps.pv == approx(annual_energy_expected, 1e-3)
    assert aeps.hybrid == approx(annual_energy_expected, 1e-3)

    # Test user-instantiated or user-defined pv plant run in a hybrid simulation
    power_sources = {
        'pv': {
            'pv_plant': DetailedPVPlant(site=site, pv_config=pv_config),
        }
    }
    hybrid_plant = HybridSimulation(
        power_sources,
        site,
        interconnect_kw=150e3,
        simulation_options={'pv': {'skip_financial': True}})
    hybrid_plant.simulate()
    aeps = hybrid_plant.annual_energies
    assert aeps.pv == approx(annual_energy_expected, 1e-3)
    assert aeps.hybrid == approx(annual_energy_expected, 1e-3)
