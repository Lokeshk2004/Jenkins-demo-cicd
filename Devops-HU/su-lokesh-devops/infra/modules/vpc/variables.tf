variable "project_tag" {
  description = "Project tag for naming"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_cidr" {
  description = "CIDR for the public subnet"
  type        = string
}

variable "private_subnet_a_cidr" {
  description = "CIDR for private subnet A"
  type        = string
}

variable "private_subnet_b_cidr" {
  description = "CIDR for private subnet B"
  type        = string
}

variable "az_a" {
  description = "Availability zone A"
  type        = string
}

variable "az_b" {
  description = "Availability zone B"
  type        = string
}
