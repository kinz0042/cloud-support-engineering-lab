# A mocked provider and plan-only runs ensure this file cannot create AWS resources.
mock_provider "aws" {
  override_during = plan
}

override_resource {
  target = aws_security_group.client
  values = { id = "sg-00000000000000001" }
}

override_resource {
  target = aws_security_group.service
  values = { id = "sg-00000000000000002" }
}

variables {
  aws_region = "us-east-1"
  vpc_id     = "vpc-00000000000000001"
}

run "initial_service_ingress_absent" {
  command = plan
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.service_from_client) == 0
    error_message = "The initial scenario must have no configured service ingress rule."
  }
  assert {
    condition     = aws_vpc_security_group_egress_rule.client_to_service.referenced_security_group_id == aws_security_group.service.id && aws_vpc_security_group_egress_rule.client_to_service.from_port == 8081 && aws_vpc_security_group_egress_rule.client_to_service.to_port == 8081 && aws_vpc_security_group_egress_rule.client_to_service.ip_protocol == "tcp"
    error_message = "The client egress must target the service group and the single TCP port."
  }
}

run "recovery_is_scoped_to_the_client_group" {
  command = plan
  variables {
    allow_client_ingress = true
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.service_from_client) == 1 && aws_vpc_security_group_ingress_rule.service_from_client[0].referenced_security_group_id == aws_security_group.client.id && aws_vpc_security_group_ingress_rule.service_from_client[0].security_group_id == aws_security_group.service.id && aws_vpc_security_group_ingress_rule.service_from_client[0].from_port == 8081 && aws_vpc_security_group_ingress_rule.service_from_client[0].to_port == 8081 && aws_vpc_security_group_ingress_rule.service_from_client[0].ip_protocol == "tcp"
    error_message = "Recovery must add only the intended client group and TCP port."
  }
}

run "reject_privileged_port" {
  command = plan
  variables {
    service_port = 80
  }
  expect_failures = [var.service_port]
}

run "reject_invalid_vpc" {
  command = plan
  variables {
    vpc_id = "production"
  }
  expect_failures = [var.vpc_id]
}
