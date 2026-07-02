# The database moves OUT of the cluster: RDS owns patching, backups, failover.
# Trade-off talk track: you give up "kubectl exec psql" convenience and pay more,
# you gain point-in-time recovery, automated minor upgrades, and a database that
# survives the cluster being deleted.

# RDS places its network interfaces into these (private!) subnets.
resource "aws_db_subnet_group" "dojo" {
  name       = "${var.project_name}-db"
  subnet_ids = local.private_subnets
  tags       = local.tags
}

# Postgres reachable from the EKS worker nodes and NOWHERE else — the same
# zero-trust idea as the NetworkPolicies in lab 28, one layer down.
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds"
  description = "Postgres from EKS nodes only."
  vpc_id      = local.vpc_id

  ingress {
    description     = "Postgres from EKS worker nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [local.node_sg_id] # SG-to-SG: survives node churn, unlike CIDRs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_db_instance" "dojo" {
  identifier     = var.project_name
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro" # smallest sane class (~$12/mo — destroy after the lab!)

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "dojo"
  username = "dojo"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.dojo.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  multi_az                = false # learning. Production: true = standby in another AZ
  backup_retention_period = 7     # enables point-in-time recovery
  apply_immediately       = true

  # Learning conveniences — in production both of these flip:
  skip_final_snapshot = true
  deletion_protection = false

  tags = local.tags
}
