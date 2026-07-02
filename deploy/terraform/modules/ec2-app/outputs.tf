output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.this.public_ip
}

output "public_dns" {
  description = "Public DNS name of the instance."
  value       = aws_instance.this.public_dns
}

output "ssh_command" {
  description = "Connect to the box (run from the directory holding the .pem)."
  value       = "ssh -i ${var.private_key_path} ubuntu@${aws_eip.this.public_ip}"
}

output "ansible_inventory_line" {
  description = "Paste into deploy/ansible/inventory.ini under [dojo]."
  value       = "dojo ansible_host=${aws_eip.this.public_ip} ansible_user=ubuntu"
}
