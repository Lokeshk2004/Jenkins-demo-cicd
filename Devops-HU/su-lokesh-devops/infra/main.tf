terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_tag
      ManagedBy = "terraform"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
}

# -----------------------------------------------
# Data Sources
# -----------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

# -----------------------------------------------
# Module: VPC
# -----------------------------------------------
module "vpc" {
  source = "./modules/vpc"

  project_tag           = var.project_tag
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidr    = var.public_subnet_cidr
  private_subnet_a_cidr = var.private_subnet_a_cidr
  private_subnet_b_cidr = var.private_subnet_b_cidr
  az_a                  = data.aws_availability_zones.available.names[0]
  az_b                  = data.aws_availability_zones.available.names[1]
}

# -----------------------------------------------
# Module: IAM
# -----------------------------------------------
module "iam" {
  source = "./modules/iam"

  project_tag      = var.project_tag
  eks_cluster_name = var.eks_cluster_name
  oidc_provider_url = module.eks.oidc_provider_url
}

# -----------------------------------------------
# Module: Security Groups
# -----------------------------------------------
module "security_groups" {
  source = "./modules/security_groups"

  project_tag = var.project_tag
  vpc_id      = module.vpc.vpc_id
  vpc_cidr    = var.vpc_cidr
}

# -----------------------------------------------
# Module: EKS
# -----------------------------------------------
module "eks" {
  source = "./modules/eks"

  project_tag           = var.project_tag
  cluster_name          = var.eks_cluster_name
  kubernetes_version    = var.kubernetes_version
  subnet_ids            = [module.vpc.private_subnet_a_id, module.vpc.private_subnet_b_id]
  cluster_role_arn      = module.iam.eks_cluster_role_arn
  node_role_arn         = module.iam.eks_node_role_arn
  node_instance_type    = var.eks_node_instance_type
  node_desired_count    = var.eks_node_desired_count
  node_min_count        = var.eks_node_min_count
  node_max_count        = var.eks_node_max_count
  node_security_group_id = module.security_groups.eks_node_sg_id
  cluster_security_group_id = module.security_groups.eks_cluster_sg_id
  ebs_csi_role_arn          = module.iam.ebs_csi_driver_role_arn
}

# -----------------------------------------------
# Module: EC2 Bastion
# -----------------------------------------------
module "ec2" {
  source = "./modules/ec2"

  project_tag       = var.project_tag
  subnet_id         = module.vpc.private_subnet_a_id
  instance_type     = var.bastion_instance_type
  security_group_id = module.security_groups.bastion_sg_id
  iam_instance_profile = module.iam.bastion_instance_profile_name
}

# -----------------------------------------------
# Module: GCR
# -----------------------------------------------
module "gcr" {
  source = "./modules/gcr"

  project_tag    = var.project_tag
  gcp_project_id = var.gcp_project_id
}
