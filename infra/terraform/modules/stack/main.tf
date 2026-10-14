# One CareSlot environment. Composes capability modules; the module *interfaces* (network,
# secrets, database, observability, app) are cloud-neutral, so porting to another provider means
# reimplementing module internals, not the environments that use them.
resource "azurerm_resource_group" "this" {
  name     = "rg-${var.name}"
  location = var.location
  tags     = local.tags
}

locals {
  tags = merge(var.tags, {
    service     = "careslot"
    environment = var.environment
    data-class  = "health-personal" # drives policy: EU-only regions, no public endpoints
  })
}

module "network" {
  source              = "../network"
  name                = var.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

module "secrets" {
  source              = "../secrets"
  name                = var.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

module "observability" {
  source              = "../observability"
  name                = var.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

module "database" {
  source               = "../database"
  name                 = var.name
  location             = var.location
  resource_group_name  = azurerm_resource_group.this.name
  subnet_id            = module.network.database_subnet_id
  private_dns_zone_id  = module.network.postgres_private_dns_zone_id
  key_vault_id         = module.secrets.key_vault_id
  sku_name             = var.database_sku
  high_availability    = var.high_availability
  geo_redundant_backup = var.geo_redundant_backup
  tags                 = local.tags
}

module "app" {
  source                     = "../app"
  name                       = var.name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  environment                = var.environment
  subnet_id                  = module.network.app_subnet_id
  key_vault_id               = module.secrets.key_vault_id
  key_vault_uri              = module.secrets.key_vault_uri
  log_analytics_workspace_id = module.observability.log_analytics_workspace_id
  api_image                  = var.api_image
  web_image                  = var.web_image
  api_min_replicas           = var.api_min_replicas
  tags                       = local.tags
}
