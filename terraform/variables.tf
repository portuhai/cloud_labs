variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository in format owner/repo"
  default     = "portuhai/cloud_labs"
}

variable "alert_email" {
  type    = string
  default = "alinaportuhai@gmail.com"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Master password for RDS PostgreSQL"
}

variable "jwt_secret" {
  type        = string
  sensitive   = true
  description = "Secret key for signing JWT tokens"
}

variable "admin_password" {
  type        = string
  sensitive   = true
  default     = "admin123"
  description = "Password for /api/login endpoint"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Docker image tag (commit SHA in CI/CD)"
}