resource "aws_ecr_repository" "app" {
  name                 = "cloud-lab-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # Щоб terraform destroy видалив репозиторій навіть з образами всередині
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "URL of the ECR repository"
}