variable "enable_analytics" {
  type        = bool
  default     = false
  description = "Explicit opt-in for billable Glue, private networking, and Redshift Serverless resources."
}
data "aws_availability_zones" "available" { state = "available" }
data "aws_caller_identity" "current" {}
locals {
  analytics_count = var.enable_analytics ? 1 : 0
  catalog_columns = {
    event_id    = "string", shipment_id = "string", status = "string", event_time = "string",
    revision    = "bigint", depot_id = "string", longitude = "double", latitude = "double",
    source_date = "string", ingested_at = "string"
  }
}
resource "aws_vpc" "analytics" {
  count                = local.analytics_count
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "belgiflow-private" }
}
resource "aws_subnet" "analytics" {
  count                   = var.enable_analytics ? 3 : 0
  vpc_id                  = aws_vpc.analytics[0].id
  cidr_block              = cidrsubnet("10.42.0.0/16", 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
}
resource "aws_route_table" "analytics" {
  count  = local.analytics_count
  vpc_id = aws_vpc.analytics[0].id
}
resource "aws_route_table_association" "analytics" {
  count          = var.enable_analytics ? 3 : 0
  subnet_id      = aws_subnet.analytics[count.index].id
  route_table_id = aws_route_table.analytics[0].id
}
resource "aws_security_group" "tasks" {
  count  = local.analytics_count
  name   = "belgiflow-private-tasks"
  vpc_id = aws_vpc.analytics[0].id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "endpoints" {
  count  = local.analytics_count
  name   = "belgiflow-private-endpoints"
  vpc_id = aws_vpc.analytics[0].id
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks[0].id]
  }
}
resource "aws_vpc_endpoint" "s3" {
  count             = local.analytics_count
  vpc_id            = aws_vpc.analytics[0].id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.analytics[0].id]
}
resource "aws_vpc_endpoint" "services" {
  for_each            = var.enable_analytics ? toset(["ecr.api", "ecr.dkr", "logs", "glue", "redshift-data", "redshift-serverless"]) : toset([])
  vpc_id              = aws_vpc.analytics[0].id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.analytics[*].id
  security_group_ids  = [aws_security_group.endpoints[0].id]
}
resource "aws_iam_role" "redshift_copy" {
  count = local.analytics_count
  name  = "belgiflow-redshift-copy"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = ["redshift.amazonaws.com", "redshift-serverless.amazonaws.com"] } }]
  })
}
resource "aws_iam_role_policy" "redshift_copy" {
  count = local.analytics_count
  role  = aws_iam_role.redshift_copy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.lake.arn}/belgiflow/products/*" },
      { Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = aws_s3_bucket.lake.arn }
    ]
  })
}
resource "aws_redshiftserverless_namespace" "analytics" {
  count                 = local.analytics_count
  namespace_name        = "belgiflow"
  db_name               = "belgiflow"
  admin_username        = "belgiflow_admin"
  manage_admin_password = true
  iam_roles             = [aws_iam_role.redshift_copy[0].arn]
  default_iam_role_arn  = aws_iam_role.redshift_copy[0].arn
  log_exports           = ["userlog", "connectionlog", "useractivitylog"]
}
resource "aws_security_group" "redshift" {
  count  = local.analytics_count
  name   = "belgiflow-redshift-private"
  vpc_id = aws_vpc.analytics[0].id
  ingress {
    from_port       = 5439
    to_port         = 5439
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks[0].id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_redshiftserverless_workgroup" "analytics" {
  count                = local.analytics_count
  workgroup_name       = "belgiflow"
  namespace_name       = aws_redshiftserverless_namespace.analytics[0].namespace_name
  base_capacity        = 8
  publicly_accessible  = false
  enhanced_vpc_routing = true
  subnet_ids           = aws_subnet.analytics[*].id
  security_group_ids   = [aws_security_group.redshift[0].id]
}
resource "aws_redshiftserverless_usage_limit" "daily" {
  count         = local.analytics_count
  resource_arn  = aws_redshiftserverless_workgroup.analytics[0].arn
  usage_type    = "serverless-compute"
  amount        = 10
  period        = "daily"
  breach_action = "deactivate"
}
resource "aws_iam_role" "glue" {
  count = local.analytics_count
  name  = "belgiflow-glue"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "glue.amazonaws.com" } }]
  })
}
resource "aws_iam_role_policy" "glue" {
  count = local.analytics_count
  role  = aws_iam_role.glue[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.lake.arn}/belgiflow/*" },
      { Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = aws_s3_bucket.lake.arn },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*" }
    ]
  })
}
resource "aws_s3_object" "glue_script" {
  count  = local.analytics_count
  bucket = aws_s3_bucket.lake.id
  key    = "belgiflow/scripts/glue_compact.py"
  source = "${path.module}/../jobs/glue_compact.py"
  etag   = filemd5("${path.module}/../jobs/glue_compact.py")
}
resource "aws_glue_job" "compaction" {
  count             = local.analytics_count
  name              = "belgiflow-event-compaction"
  role_arn          = aws_iam_role.glue[0].arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0
  execution_property { max_concurrent_runs = 1 }
  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.glue_script[0].key}"
  }
  default_arguments = {
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://${aws_s3_bucket.lake.id}/belgiflow/glue-temp/"
    "--INPUT_PATH"                       = "s3://${aws_s3_bucket.lake.id}/belgiflow/inputs/not-configured"
    "--OUTPUT_PATH"                      = "s3://${aws_s3_bucket.lake.id}/belgiflow/outputs/not-configured"
    "--EXPECTED_SHIPMENTS"               = "0"
  }
}
resource "aws_glue_catalog_database" "analytics" {
  count = local.analytics_count
  name  = "belgiflow"
}
resource "aws_glue_catalog_table" "events" {
  count         = local.analytics_count
  database_name = aws_glue_catalog_database.analytics[0].name
  name          = "raw_events"
  table_type    = "EXTERNAL_TABLE"
  parameters    = { classification = "parquet" }
  partition_keys {
    name = "batch_date"
    type = "string"
  }
  partition_keys {
    name = "generation"
    type = "string"
  }
  storage_descriptor {
    location      = "s3://${aws_s3_bucket.lake.id}/belgiflow/catalog/raw_events/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }
    dynamic "columns" {
      for_each = ["event_id", "shipment_id", "status", "event_time", "revision", "depot_id", "longitude", "latitude", "source_date", "ingested_at"]
      content {
        name = columns.value
        type = local.catalog_columns[columns.value]
      }
    }
  }
}
resource "aws_iam_role_policy" "pipeline_analytics" {
  count = local.analytics_count
  role  = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.lake.arn}/belgiflow/*" },
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.lake.arn },
      { Effect = "Allow", Action = ["glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"], Resource = aws_glue_job.compaction[0].arn },
      { Effect = "Allow", Action = ["redshift-data:BatchExecuteStatement", "redshift-data:ExecuteStatement"], Resource = aws_redshiftserverless_workgroup.analytics[0].arn },
      { Effect = "Allow", Action = ["redshift-data:DescribeStatement", "redshift-data:CancelStatement"], Resource = "*" },
      { Effect = "Allow", Action = ["redshift-serverless:GetCredentials", "redshift-serverless:GetWorkgroup"], Resource = aws_redshiftserverless_workgroup.analytics[0].arn },
      { Effect = "Allow", Action = ["glue:GetTable", "glue:BatchCreatePartition"], Resource = [
        "arn:aws:glue:${var.region}:${data.aws_caller_identity.current.account_id}:catalog",
        "arn:aws:glue:${var.region}:${data.aws_caller_identity.current.account_id}:database/belgiflow",
        "arn:aws:glue:${var.region}:${data.aws_caller_identity.current.account_id}:table/belgiflow/raw_events"
      ] }
    ]
  })
}
output "analytics" {
  value = var.enable_analytics ? {
    workgroup       = aws_redshiftserverless_workgroup.analytics[0].workgroup_name
    redshift_host   = aws_redshiftserverless_workgroup.analytics[0].endpoint[0].address
    copy_role       = aws_iam_role.redshift_copy[0].arn
    glue_job        = aws_glue_job.compaction[0].name
    glue_database   = aws_glue_catalog_database.analytics[0].name
    private_subnets = aws_subnet.analytics[*].id
    task_group      = aws_security_group.tasks[0].id
  } : null
}
