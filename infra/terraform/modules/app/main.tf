# Container Apps: the API (>= 2 replicas across zones), the web frontend, and the daily
# retention job. A user-assigned identity reads secrets from Key Vault - no secrets in config.
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${var.name}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  infrastructure_subnet_id   = var.subnet_id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  zone_redundancy_enabled    = true
  tags                       = var.tags
}

locals {
  # Secrets resolved from Key Vault at runtime by the managed identity.
  kv_secrets = {
    "database-url"    = "careslot-database-url"
    "keks"            = "careslot-keks"
    "blind-index-key" = "careslot-blind-index-key"
    "jwt-public-key"  = "careslot-jwt-public-key"
  }
  common_env = {
    CARESLOT_ENVIRONMENT = var.environment
  }
  secret_env = {
    CARESLOT_DATABASE_URL    = "database-url"
    CARESLOT_KEKS            = "keks"
    CARESLOT_BLIND_INDEX_KEY = "blind-index-key"
    CARESLOT_JWT_PUBLIC_KEY  = "jwt-public-key"
  }
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${var.name}-api"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "secret" {
    for_each = local.kv_secrets
    content {
      name                = secret.key
      key_vault_secret_id = "${var.key_vault_uri}secrets/${secret.value}"
      identity            = azurerm_user_assigned_identity.app.id
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    container {
      name   = "api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.common_env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = 8000
      }
    }
  }
}

resource "azurerm_container_app" "web" {
  name                         = "ca-${var.name}-web"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 3
    container {
      name   = "web"
      image  = var.web_image
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }
}

# Daily retention job (careslot.jobs.retention) - GDPR storage limitation.
resource "azurerm_container_app_job" "retention" {
  name                         = "caj-${var.name}-retention"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  replica_timeout_in_seconds   = 1800
  tags                         = var.tags

  schedule_trigger_config {
    cron_expression = "15 2 * * *" # 02:15 UTC, outside clinic hours
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "secret" {
    for_each = local.kv_secrets
    content {
      name                = secret.key
      key_vault_secret_id = "${var.key_vault_uri}secrets/${secret.value}"
      identity            = azurerm_user_assigned_identity.app.id
    }
  }

  template {
    container {
      name    = "retention"
      image   = var.api_image
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["python", "-m", "careslot.jobs.retention"]

      dynamic "env" {
        for_each = local.secret_env
        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }
}
