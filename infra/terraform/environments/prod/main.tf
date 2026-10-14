# Production: zone-redundant database and API, geo-redundant backups (see NFR doc).
module "careslot" {
  source      = "../../modules/stack"
  name        = "careslot-prod"
  environment = "production"
  location    = "swedencentral"
  api_image   = var.api_image
  web_image   = var.web_image
}
