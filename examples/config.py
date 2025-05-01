"""
config
"""

# this is the part that needs to be adapted on another environment
# type of auth
AUTH = "API_KEY"
# OCI general
#  poc/volvo
COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaau6vhnjavhh7iqajg47f6d4cyft3aizw6r2vcp3wb3nmg3kf3pa6a"

#
# General
#
AGENT_NAME = "EXAMPLE01"

DEBUG = False


REGION = "eu-frankfurt-1"
# OCI Genai service endpoint
SERVICE_ENDPOINT = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"

# APM integration
ENABLE_TRACING = True

# this is the base URL of the APM domain we're using
APM_BASE_URL = f"https://aaaadec2jjn3maaaaaaaaach4e.apm-agt.{REGION}.oci.oraclecloud.com/20200101"
APM_CONTENT_TYPE = "application/json"