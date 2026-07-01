# Latest Ubuntu 24.04 LTS (Noble) AMI, published by Canonical.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- SSH key pair -----------------------------------------------------------
# Default: Terraform generates an ed25519 key pair and writes the private key to
# private_key_path (dojo-key.pem). Set generate_ssh_key = false to upload your own
# public key instead (public_key_path). Either way an aws_key_pair is created and
# the instance uses it. NOTE: when generating, the private key is stored in
# terraform.tfstate too — both the .pem and the state file are gitignored.
resource "tls_private_key" "dojo" {
  count     = var.generate_ssh_key ? 1 : 0
  algorithm = "ED25519"
}

resource "local_sensitive_file" "private_key" {
  count           = var.generate_ssh_key ? 1 : 0
  content         = tls_private_key.dojo[0].private_key_openssh
  filename        = var.private_key_path
  file_permission = "0400"
}

resource "aws_key_pair" "dojo" {
  key_name   = "${var.project_name}-key"
  public_key = var.generate_ssh_key ? tls_private_key.dojo[0].public_key_openssh : file(var.public_key_path)
}

# Public entrypoint firewall: SSH from you only; HTTP/HTTPS from anywhere (Caddy).
# We deliberately do NOT open app/db ports (8080, 5432, ...) to the internet.
resource "aws_security_group" "dojo" {
  name        = "${var.project_name}-sg"
  description = "DevOps Dojo: SSH from admin IP, HTTP/HTTPS public."

  ingress {
    description = "SSH (admin only)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = var.project_name }
}

resource "aws_instance" "dojo" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.dojo.key_name
  vpc_security_group_ids = [aws_security_group.dojo.id]

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  tags = {
    Name    = var.project_name
    Project = var.project_name
  }
}

# Stable public IP so the address survives reboots (and DNS stays valid).
resource "aws_eip" "dojo" {
  instance = aws_instance.dojo.id
  domain   = "vpc"
  tags     = { Project = var.project_name }
}
