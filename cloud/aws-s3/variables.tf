variable "aws_region" {
  description = "AWS region for the approved sandbox."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name reserved for this disposable lab."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name)) && !can(regex("[.][.]", var.bucket_name)) && !can(regex("^[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+$", var.bucket_name))
    error_message = "Use a 3–63 character lowercase S3 bucket name with no adjacent periods or IP address form."
  }
}
