variable "api_image" {
  type        = string
  description = "Immutable image reference (digest), built and scanned by CI."
}
variable "web_image" {
  type        = string
  description = "Immutable image reference (digest), built and scanned by CI."
}
