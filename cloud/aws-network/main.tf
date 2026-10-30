terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# These groups are deliberately not attached to an instance or interface.
resource "aws_security_group" "client" {
  name_prefix = "relay-lab-client-"
  description = "Synthetic client security group for an isolated support lab"
  vpc_id      = var.vpc_id
  tags = {
    Purpose = "synthetic-support-lab"
  }
}

resource "aws_security_group" "service" {
  name_prefix = "relay-lab-service-"
  description = "Synthetic service security group for an isolated support lab"
  vpc_id      = var.vpc_id
  tags = {
    Purpose = "synthetic-support-lab"
  }
}

resource "aws_vpc_security_group_egress_rule" "client_to_service" {
  security_group_id            = aws_security_group.client.id
  referenced_security_group_id = aws_security_group.service.id
  ip_protocol                  = "tcp"
  from_port                    = var.service_port
  to_port                      = var.service_port
  description                  = "Synthetic client to service port"
}

# The incident begins with this rule absent. Remediation requires explicit input.
resource "aws_vpc_security_group_ingress_rule" "service_from_client" {
  count                        = var.allow_client_ingress ? 1 : 0
  security_group_id            = aws_security_group.service.id
  referenced_security_group_id = aws_security_group.client.id
  ip_protocol                  = "tcp"
  from_port                    = var.service_port
  to_port                      = var.service_port
  description                  = "Synthetic client to service port"
}

output "client_security_group_id" {
  value = aws_security_group.client.id
}

output "service_security_group_id" {
  value = aws_security_group.service.id
}

output "scenario_configuration" {
  description = "A configuration state, not proof that any actual path is reachable."
  value       = var.allow_client_ingress ? "ingress_rule_configured" : "ingress_rule_absent"
}
