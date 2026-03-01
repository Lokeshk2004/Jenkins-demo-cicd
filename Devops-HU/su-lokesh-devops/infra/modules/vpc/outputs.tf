output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "private_subnet_a_id" {
  description = "ID of private subnet A"
  value       = aws_subnet.private_a.id
}

output "private_subnet_b_id" {
  description = "ID of private subnet B"
  value       = aws_subnet.private_b.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.main.id
}
