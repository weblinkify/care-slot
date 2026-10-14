variable "name" { type = string }
variable "environment" { type = string }
variable "location" {
  type        = string
  description = "EU/EEA region only (data residency)."
  validation {
    condition     = contains(["swedencentral", "northeurope", "westeurope", "norwayeast", "finlandcentral"], var.location)
    error_message = "Health data must stay in an approved EU/EEA region."
  }
}
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "database_sku" {
  type    = string
  default = "GP_Standard_D2ds_v5"
}
variable "high_availability" {
  type    = bool
  default = true
}
variable "geo_redundant_backup" {
  type    = bool
  default = true
}
variable "api_min_replicas" {
  type    = number
  default = 2
}
variable "tags" {
  type    = map(string)
  default = {}
}
