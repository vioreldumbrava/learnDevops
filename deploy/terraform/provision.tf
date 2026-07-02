# --- Lab 44: Terraform → Ansible handoff (off by default) --------------------
# Provisioning (Terraform) and configuration (Ansible) stay two tools; this
# wires them together so one `terraform apply` ends with a configured, running
# app. Provisioners are demo-style glue and a documented last resort — they
# live outside plan/state and have no drift detection. In CI you'd run these
# as two pipeline steps (provision, then configure). Run from WSL/Linux: the
# local-exec needs bash + ansible-playbook on PATH.

variable "run_ansible" {
  description = "Lab 44: run the Ansible playbook (roles layout, dynamic inventory) after provisioning."
  type        = bool
  default     = false
}

variable "repo_url" {
  description = "Lab 44: git URL of your fork, passed to the playbook as repo_url."
  type        = string
  default     = ""
}

variable "ansible_extra_args" {
  description = "Lab 44: extra ansible-playbook args, e.g. \"-e postgres_password=... -e site_domain=:80\"."
  type        = string
  default     = ""
}

resource "null_resource" "configure" {
  count = var.run_ansible ? 1 : 0

  # New instance or new address => configure again.
  triggers = {
    instance_id = aws_instance.dojo.id
    public_ip   = aws_eip.dojo.public_ip
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/../ansible"
    interpreter = ["bash", "-c"]
    # The EC2 instance answers SSH well after `apply` returns, so poll first.
    # The playbook then targets the dynamic inventory — no IP is passed here;
    # Ansible asks AWS for it (see deploy/ansible/inventory/aws_ec2.yaml).
    command = <<-EOT
      set -euo pipefail
      echo "Waiting for SSH on ${aws_eip.dojo.public_ip} ..."
      for i in $(seq 1 30); do
        ssh -i ${var.private_key_path} -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 \
            ubuntu@${aws_eip.dojo.public_ip} true 2>/dev/null && break
        sleep 10
      done
      ansible-playbook -i inventory/aws_ec2.yaml site.yml \
        -e repo_url=${var.repo_url} ${var.ansible_extra_args}
    EOT
  }
}
