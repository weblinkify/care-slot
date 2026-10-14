variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "environment" { type = string }
variable "subnet_id" { type = string }
variable "key_vault_id" { type = string }
variable "key_vault_uri" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "api_min_replicas" {
  type    = number
  default = 2 # one per zone: survives a zone outage within the 99.9 % SLO
}
variable "api_max_replicas" {
  type    = number
  default = 6
}
variable "tags" {
  type    = map(string)
  default = {}
}
