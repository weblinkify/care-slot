# Managed PostgreSQL 16: private access only, zone-redundant HA, PITR with 35-day retention and
# geo-redundant backups (docs/non-functional-requirements.md: RPO <= 5 min, RTO <= 1 h).
resource "random_password" "admin" {
  length  = 32
  special = false
}

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "psql-${var.name}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  version                       = "16"
  sku_name                      = var.sku_name
  storage_mb                    = var.storage_mb
  delegated_subnet_id           = var.subnet_id
  private_dns_zone_id           = var.private_dns_zone_id
  public_network_access_enabled = false
  administrator_login           = "careslot_admin"
  administrator_password        = random_password.admin.result
  backup_retention_days         = 35
  geo_redundant_backup_enabled  = var.geo_redundant_backup
  zone                          = "1"
  tags                          = var.tags

  dynamic "high_availability" {
    for_each = var.high_availability ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = "2"
    }
  }
}

resource "azurerm_postgresql_flexible_server_database" "careslot" {
  name      = "careslot"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# The admin password is generated here and stored only in Key Vault. The application uses a
# separate least-privilege role (INSERT/SELECT only on aud_entries - ADR-0004), created by a
# bootstrap migration step, not by Terraform.
resource "azurerm_key_vault_secret" "admin_password" {
  name         = "postgres-admin-password"
  value        = random_password.admin.result
  key_vault_id = var.key_vault_id
}
