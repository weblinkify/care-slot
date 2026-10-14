output "api_fqdn" { value = azurerm_container_app.api.ingress[0].fqdn }
output "web_fqdn" { value = azurerm_container_app.web.ingress[0].fqdn }
