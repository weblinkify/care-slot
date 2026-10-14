# Development: smallest sizes, no HA, local backups only. Synthetic data only.
module "careslot" {
  source               = "../../modules/stack"
  name                 = "careslot-dev"
  environment          = "staging"
  location             = "swedencentral"
  api_image            = var.api_image
  web_image            = var.web_image
  database_sku         = "B_Standard_B1ms"
  high_availability    = false
  geo_redundant_backup = false
  api_min_replicas     = 1
}
