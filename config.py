import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://healthcare_user:abhdkGDafnKD-EcZk+#>FR^{ğn-mnp:E%54Fv@localhost/healthcare_db"
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"