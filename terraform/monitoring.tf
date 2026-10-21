resource "aws_sns_topic" "alerts" {
  name = "cloud-lab-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "alinaportuhai@gmail.com"
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "ecs-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [aws_sns_topic.alerts.arn]
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.main.name
  }
}