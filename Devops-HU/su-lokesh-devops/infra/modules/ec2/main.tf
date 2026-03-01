# -----------------------------------------------
# EC2 Bastion Module — Private subnet, SSM access
# -----------------------------------------------

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = var.iam_instance_profile
  associate_public_ip_address = false

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y aws-cli jq

    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl /usr/local/bin/

    # Install kubeseal
    KUBESEAL_VERSION=$(curl -s https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest | jq -r '.tag_name' | sed 's/v//')
    curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v$${KUBESEAL_VERSION}/kubeseal-$${KUBESEAL_VERSION}-linux-amd64.tar.gz"
    tar -xvzf kubeseal-$${KUBESEAL_VERSION}-linux-amd64.tar.gz kubeseal
    mv kubeseal /usr/local/bin/

    # Install Helm
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  EOF

  tags = {
    Name = "${var.project_tag}-bastion"
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }
}
