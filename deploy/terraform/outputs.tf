output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.dojo.public_ip
}

output "public_dns" {
  description = "Public DNS name of the instance."
  value       = aws_instance.dojo.public_dns
}

output "private_key_file" {
  description = "Where the SSH private key lives (generated) or a reminder (bring-your-own)."
  value       = var.generate_ssh_key ? var.private_key_path : "your own key (public_key_path was used)"
}

output "ssh_command" {
  description = "Connect to the box. Run from the repo root, where dojo-key.pem lives."
  value       = "ssh -i dojo-key.pem ubuntu@${aws_eip.dojo.public_ip}"
}

output "ansible_inventory_line" {
  description = "Paste into deploy/ansible/inventory.ini under [dojo]."
  value       = "dojo ansible_host=${aws_eip.dojo.public_ip} ansible_user=ubuntu"
}
