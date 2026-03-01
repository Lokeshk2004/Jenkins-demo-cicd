terraform {
  backend "s3" {
    bucket         = "su-devops-lokesh26-tfstate"
    key            = "eks-platform/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "su-devops-lokesh26-tflock"
    encrypt        = true
  }
}
