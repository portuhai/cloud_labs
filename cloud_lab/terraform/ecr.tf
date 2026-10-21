resource "aws_ecr_repository" "app" {
  name                 = "cloud-lab-app"
  image_tag_mutability = "MUTABLE"
}