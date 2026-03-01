variable "project_tag" {
  description = "Project tag for naming"
  type        = string
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "oidc_provider_url" {
  description = "OIDC provider URL from EKS cluster"
  type        = string
}
