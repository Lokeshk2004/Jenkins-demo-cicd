output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_role_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = aws_iam_role.eks_node.arn
}

output "ebs_csi_driver_role_arn" {
  description = "ARN of the EBS CSI driver IRSA role"
  value       = aws_iam_role.ebs_csi_driver.arn
}

output "bastion_instance_profile_name" {
  description = "Name of the bastion IAM instance profile"
  value       = aws_iam_instance_profile.bastion.name
}
