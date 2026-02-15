"""Physical constants used throughout RESA Pro.

All values in SI units unless otherwise noted.
"""

import math

# Universal constants
R_UNIVERSAL = 8.31446261815324  # J/(mol·K) — universal gas constant
AVOGADRO = 6.02214076e23  # 1/mol
BOLTZMANN = 1.380649e-23  # J/K
STEFAN_BOLTZMANN = 5.670374419e-8  # W/(m²·K⁴)
PLANCK = 6.62607015e-34  # J·s

# Gravitational
G_0 = 9.80665  # m/s² — standard gravitational acceleration
G_UNIVERSAL = 6.67430e-11  # m³/(kg·s²)

# Atmospheric
P_ATM = 101325.0  # Pa — standard atmospheric pressure
T_ATM = 288.15  # K — standard atmospheric temperature (15°C)
RHO_AIR_STP = 1.225  # kg/m³ — air density at STP

# Thermodynamic
T_ABSOLUTE_ZERO = 0.0  # K
T_CELSIUS_OFFSET = 273.15  # K

# Mathematical
PI = math.pi
TWO_PI = 2.0 * math.pi
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

# Conversion factors
BAR_TO_PA = 1.0e5
PA_TO_BAR = 1.0e-5
MPA_TO_PA = 1.0e6
PA_TO_MPA = 1.0e-6
PSI_TO_PA = 6894.757293168
PA_TO_PSI = 1.0 / PSI_TO_PA
MM_TO_M = 1.0e-3
M_TO_MM = 1.0e3
INCH_TO_M = 0.0254
M_TO_INCH = 1.0 / INCH_TO_M
LBF_TO_N = 4.4482216152605
N_TO_LBF = 1.0 / LBF_TO_N
LBM_TO_KG = 0.45359237
KG_TO_LBM = 1.0 / LBM_TO_KG
