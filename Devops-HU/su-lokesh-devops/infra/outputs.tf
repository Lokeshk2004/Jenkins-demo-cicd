# -----------------------------------------------
# VPC Outputs
# -----------------------------------------------
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = module.vpc.public_subnet_id
}

output "private_subnet_a_id" {
  description = "ID of private subnet A"
  value       = module.vpc.private_subnet_a_id
}

output "private_subnet_b_id" {
  description = "ID of private subnet B"
  value       = module.vpc.private_subnet_b_id
}

# -----------------------------------------------
# EKS Outputs
# -----------------------------------------------
output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_certificate_authority" {
  description = "EKS cluster CA certificate"
  value       = module.eks.cluster_certificate_authority
  sensitive   = true
}

output "eks_oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  value       = module.eks.oidc_provider_arn
}

# -----------------------------------------------
# Bastion Outputs
# -----------------------------------------------
output "bastion_instance_id" {
  description = "Instance ID of the bastion host"
  value       = module.ec2.bastion_instance_id
}

# -----------------------------------------------
# GCR Outputs
# -----------------------------------------------
output "gcr_secret_arn" {
  description = "ARN of the Secrets Manager secret storing GCR SA key"
  value       = module.gcr.secret_arn
}
