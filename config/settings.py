# ─── System Constants ────────────────────────────────────────────────────────
MAX_BINS           = 100
MAX_VEHICLES       = 20
MAX_DRIVERS        = 30
MAX_ZONES          = 10
FILL_THRESHOLD     = 70        # % — bin is "critical" above this
MAX_DAILY_DISTANCE = 200       # km per vehicle per day
MAINTENANCE_KM     = 500       # km before mandatory maintenance
EMERGENCY_RESPONSE = 30        # minutes — max response time for overflow
BUDGET_PER_DAY     = 50000     # ₹ optional budget cap

# Waste-type codes
WASTE_TYPES = ["Dry", "Wet", "Mixed", "Hazardous"]

# Vehicle types
VEHICLE_TYPES = ["Standard", "Compactor", "HazMat", "Mini"]

# Priority levels (lower number = higher priority)
PRIORITY = {"Hazardous": 1, "Overflow": 2, "Critical": 3, "Normal": 4}

# Fuel price per litre (₹)
FUEL_PRICE = 95.0

# Data file paths
DATA_DIR       = "data"
BINS_FILE      = "data/bins.json"
VEHICLES_FILE  = "data/vehicles.json"
DRIVERS_FILE   = "data/drivers.json"
ZONES_FILE     = "data/zones.json"
LOGS_FILE      = "data/collection_logs.json"
ROUTES_FILE    = "data/routes.json"
