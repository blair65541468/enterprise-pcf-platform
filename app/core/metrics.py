from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "pcf_http_requests_total",
    "HTTP requests handled by the PCF API",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "pcf_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
)
IMPORTS = Counter(
    "pcf_imports_total",
    "Completed imports",
    ["status"],
)
CALCULATION_DURATION = Histogram(
    "pcf_calculation_duration_seconds",
    "Calculation duration by engine",
    ["engine", "outcome"],
)
OPENLCA_ERRORS = Counter(
    "pcf_openlca_errors_total",
    "openLCA adapter errors",
    ["kind"],
)
TASK_RETRIES = Counter(
    "pcf_task_retries_total",
    "Celery task retries",
    ["task"],
)
CALCULATION_STATUS = Gauge(
    "pcf_calculation_status_total",
    "Current calculation count by status",
    ["status"],
)
