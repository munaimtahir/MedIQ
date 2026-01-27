# Track A: EC2 + Docker Compose Main Configuration
# Stub implementation - add actual resources

# data "aws_ami" "ubuntu" {
#   most_recent = true
#   owners      = ["099720109477"] # Canonical
# 
#   filter {
#     name   = "name"
#     values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
#   }
# 
#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }
# }
# 
# resource "aws_instance" "app" {
#   ami           = data.aws_ami.ubuntu.id
#   instance_type = var.instance_type
#   subnet_id     = var.subnet_id
#   vpc_security_group_ids = var.security_group_ids
#   key_name      = var.key_pair_name
# 
#   user_data = templatefile("${path.module}/user-data.sh", {
#     image_backend  = var.image_backend
#     image_frontend = var.image_frontend
#     database_endpoint = var.database_endpoint
#     cache_endpoint    = var.cache_endpoint
#   })
# 
#   tags = {
#     Name = "exam-platform-${var.environment}"
#   }
# }
