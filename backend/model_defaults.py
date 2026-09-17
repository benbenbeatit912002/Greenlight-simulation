"""Control names, recorded-weather presets and unchanged model defaults."""

CONTROL_NAMES = (
    "uBoil",
    "uCO2",
    "uThScr",
    "uVent",
    "uLamp",
    "uBlScr",
)


DEFAULT_TARGETS = {
    "dayTemp": 21.5,
    "nightTemp": 17.5,
    "co2": 900.0,
    "maxRh": 82.0,
}


SCENARIOS = {
    "spring": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 59,
        "label": "阿姆斯特丹 2010・春季實測",
    },
    "cloudy": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 295,
        "label": "阿姆斯特丹 2010・晚秋實測",
    },
    "summer": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 172,
        "label": "阿姆斯特丹 2010・夏季實測",
    },
    "winter": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 1,
        "label": "阿姆斯特丹 2010・冬季實測",
    },
}


RULE_BASED_DEFAULTS = {
    "lamps_on": 0,
    "lamps_off": 18,
    "lamps_day_start": -1,
    "lamps_day_stop": 366,
    "lamps_off_sun": 400,
    "lamp_rad_sum_limit": 10,
    "heat_correction": 0,
    "heat_deadzone": 5,
    "vent_heat_Pband": 4,
    "mech_dehumid_Pband": 2,
    "vent_rh_Pband": 5,
    "t_vent_off": 1,
    "vent_cold_Pband": -1,
    "thScrSpDay": 5,
    "thScrSpNight": 10,
    "thScrPband": -1,
    "thScrDeadZone": 4,
    "thScrRh": -2,
    "thScrRhPband": 2,
    "lampExtraHeat": 2,
    "blScrExtraRh": 100,
    "tHeatBand": -1,
    "co2Band": -100,
    "useBlScr": 1,
}


ADAPTER_VERSION = "2026.09-run-local-greenhouse"
