variable "project_tag" {
  description = "Project tag for naming"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for EKS cluster and nodes"
  type        = list(string)
}

variable "cluster_role_arn" {
  description = "IAM role ARN for EKS cluster"
  type        = string
}

variable "node_role_arn" {
  description = "IAM role ARN for EKS node group"
  type        = string
}

variable "node_instance_type" {
  description = "Instance type for worker nodes"
  type        = string
}

variable "node_desired_count" {
  description = "Desired number of worker nodes"
  type        = number
}

variable "node_min_count" {
  description = "Minimum number of worker nodes"
  type        = number
}

variable "node_max_count" {
  description = "Maximum number of worker nodes"
  type        = number
}

variable "node_security_group_id" {
  description = "Security group ID for worker nodes"
  type        = string
}

variable "cluster_security_group_id" {
  description = "Security group ID for EKS cluster"
  type        = string
}

variable "ebs_csi_role_arn" {
  description = "IAM role ARN for EBS CSI driver"
  type        = string
  default     = ""
}
