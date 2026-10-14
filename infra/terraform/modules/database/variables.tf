variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "key_vault_id" { type = string }
variable "sku_name" {
  type    = string
  default = "GP_Standard_D2ds_v5"
}
variable "storage_mb" {
  type    = number
  default = 65536
}
variable "high_availability" {
  type    = bool
  default = true
}
variable "geo_redundant_backup" {
  type    = bool
  default = true
}
variable "tags" {
  type    = map(string)
  default = {}
}
