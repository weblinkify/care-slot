output "app_subnet_id" { value = azurerm_subnet.app.id }
output "database_subnet_id" { value = azurerm_subnet.database.id }
output "postgres_private_dns_zone_id" { value = azurerm_private_dns_zone.postgres.id }
