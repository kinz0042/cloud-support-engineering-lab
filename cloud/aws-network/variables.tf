variable "aws_region" {
  description = "Region of the explicitly authorized disposable VPC."
  type        = string
}

variable "vpc_id" {
  description = "ID of an existing authorized disposable VPC; this module does not create one."
  type        = string
  validation {
    condition     = can(regex("^vpc-([0-9a-f]{8}|[0-9a-f]{17})$", var.vpc_id))
    error_message = "Provide a valid lowercase VPC ID for the disposable lab."
  }
}

variable "service_port" {
  description = "Single unprivileged TCP port used by the synthetic service."
  type        = number
  default     = 8081
  validation {
    condition     = var.service_port >= 1024 && var.service_port <= 65535 && floor(var.service_port) == var.service_port
    error_message = "Use a whole-number TCP port from 1024 to 65535."
  }
}

variable "allow_client_ingress" {
  description = "Add the scoped client-to-service ingress rule after investigation."
  type        = bool
  default     = false
}
