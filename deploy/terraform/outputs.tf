output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.dojo.public_ip
}

output "public_dns" {
  description = "Public DNS name of the instance."
  value       = aws_instance.dojo.public_dns
}

output "ssh_command" {
  description = "Connect to the box (adjust the key path if needed)."
  value       = "ssh -i ../../devDockerKey.pem ubuntu@${aws_eip.dojo.public_ip}"
}

output "ansible_inventory_line" {
  description = "Paste into deploy/ansible/inventory.ini under [dojo]."
  value       = "dojo ansible_host=${aws_eip.dojo.public_ip} ansible_user=ubuntu"
}
