variable "project_tag" {
  description = "Project tag for naming"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the bastion host"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID for bastion"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile name for SSM"
  type        = string
}
