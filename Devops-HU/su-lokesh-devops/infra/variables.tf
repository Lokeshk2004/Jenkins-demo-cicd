variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_tag" {
  description = "Project tag for naming resources"
  type        = string
  default     = "su-devops-lokesh26"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_a_cidr" {
  description = "CIDR for private subnet A"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_subnet_b_cidr" {
  description = "CIDR for private subnet B"
  type        = string
  default     = "10.0.3.0/24"
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "su-devops-lokesh26-eks"
}

variable "eks_node_instance_type" {
  description = "EC2 instance type for EKS node group"
  type        = string
  default     = "t2.medium"
}

variable "eks_node_desired_count" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "eks_node_min_count" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "eks_node_max_count" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "bastion_instance_type" {
  description = "EC2 instance type for bastion host"
  type        = string
  default     = "t2.micro"
}

variable "gcp_project_id" {
  description = "GCP project ID for GCR"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.29"
}
