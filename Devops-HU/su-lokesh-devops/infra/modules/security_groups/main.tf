# -----------------------------------------------
# Security Groups Module
# -----------------------------------------------

# EKS Cluster Security Group
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${var.project_tag}-eks-cluster-"
  vpc_id      = var.vpc_id
  description = "Security group for EKS cluster control plane"

  tags = { Name = "${var.project_tag}-eks-cluster-sg" }
}

resource "aws_security_group_rule" "eks_cluster_ingress_nodes" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_nodes.id
  security_group_id        = aws_security_group.eks_cluster.id
  description              = "Allow worker nodes to communicate with cluster API"
}

resource "aws_security_group_rule" "eks_cluster_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_cluster.id
  description       = "Allow all outbound traffic"
}

# EKS Node Security Group
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${var.project_tag}-eks-nodes-"
  vpc_id      = var.vpc_id
  description = "Security group for EKS worker nodes"

  tags = { Name = "${var.project_tag}-eks-nodes-sg" }
}

resource "aws_security_group_rule" "nodes_internal" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  source_security_group_id = aws_security_group.eks_nodes.id
  security_group_id        = aws_security_group.eks_nodes.id
  description              = "Allow nodes to communicate with each other"
}

resource "aws_security_group_rule" "nodes_cluster_ingress" {
  type                     = "ingress"
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_cluster.id
  security_group_id        = aws_security_group.eks_nodes.id
  description              = "Allow cluster control plane to communicate with nodes"
}

resource "aws_security_group_rule" "nodes_cluster_ingress_443" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_cluster.id
  security_group_id        = aws_security_group.eks_nodes.id
  description              = "Allow cluster API to communicate with node kubelets"
}

resource "aws_security_group_rule" "nodes_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow all outbound traffic"
}

# Bastion Security Group (SSM only — no SSH)
resource "aws_security_group" "bastion" {
  name_prefix = "${var.project_tag}-bastion-"
  vpc_id      = var.vpc_id
  description = "Security group for bastion host — SSM only, no SSH"

  tags = { Name = "${var.project_tag}-bastion-sg" }
}

resource "aws_security_group_rule" "bastion_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.bastion.id
  description       = "Allow all outbound traffic (SSM, kubectl, kubeseal)"
}

resource "aws_security_group_rule" "bastion_to_eks" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.eks_cluster.id
  description              = "Allow bastion to reach EKS API server"
}
