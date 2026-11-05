# Optional AWS implementation

The AWS path is implemented as an opt-in backend. Local tests and Terraform validation do not establish live AWS compatibility. No cloud resources have been created.

## Services and responsibilities

| Service | Role |
| --- | --- |
| S3 | Immutable typed Parquet bundles, geographic input bundles, COPY manifests, and completion pointers |
| Glue | Managed PySpark event compaction using the same transformation tested locally |
| Glue Data Catalog | Ordered event schema and explicit immutable partitions |
| Redshift Serverless | Serving warehouse with transactional staged loads and dbt models |
| ECR | Application image storage |
| ECS Fargate | On-demand orchestration task inside the private network |
| CloudWatch | Application and Glue logs |
| IAM | Separate runtime, Glue, Redshift COPY, and image-execution roles |
| VPC and endpoints | Private subnets, private warehouse access, S3 gateway access, and AWS API access |

## Authentication

Use a standard AWS profile, SSO session, or workload role. Do not paste keys into chat or commit them. The runtime obtains temporary Redshift database credentials through `redshift-serverless:GetCredentials`. dbt receives those credentials only in its child-process environment.

The AWS backend requires these non-secret settings:

```text
BELGIFLOW_BACKEND=aws
BELGIFLOW_BUCKET=<lake bucket>
BELGIFLOW_GLUE_JOB=<Glue job name>
BELGIFLOW_GLUE_DATABASE=belgiflow
BELGIFLOW_REDSHIFT_WORKGROUP=belgiflow
BELGIFLOW_REDSHIFT_DATABASE=belgiflow
BELGIFLOW_REDSHIFT_COPY_ROLE=<COPY role ARN>
```

Terraform's Fargate task supplies these settings when analytics is enabled.

## Preparation and validation

```bash
terraform -chdir=infra init -backend=false
terraform -chdir=infra fmt -check
terraform -chdir=infra validate
```

Actual deployment requires a unique bucket name, an immutable container image URI, explicit authorization, and a reviewed plan. `enable_analytics` defaults to false. Setting it true declares billable Redshift, Glue, and private networking resources.

Build and push the image to the declared ECR repository before running a Fargate task. Supply the private subnet IDs and task security group from Terraform outputs. The configuration creates an on-demand task definition rather than starting an always-running service.

## Database bootstrap

Private Redshift database access needs both AWS IAM permissions and database grants. The pipeline role must own or have sufficient privileges on the analytics schema before its first load.

Using an authorized administrator connection, create or initialize the database identity associated with the Fargate task role and grant it the required database and schema privileges. For the declared role name, that identity is normally `IAMR:belgiflow-task`. Confirm the exact `dbUser` returned by GetCredentials before granting anything.

The intended bootstrap is a schema owned by that identity, or equivalent CREATE permission on the database and USAGE/CREATE on the analytics schema. Grant access only to the project schema. The application role is not granted permission to retrieve the namespace's administrator secret.

This administrative bootstrap has not been executed. A deployed IAM policy alone is not proof that COPY or dbt will succeed.

## Private map inputs

The private Fargate network has no general internet route. Public Overture downloads should be performed locally, then published as a pinned S3 geographic bundle.

Run the local map acquisition, then run job 11 with cached map inputs and the AWS publication backend. Its result contains a `map_bundle_uri`. Set Terraform's `map_bundle_uri` to that immutable URI in the same lake bucket.

Cloud tasks then select `source_mode=s3`, verify bundle checksums, and read map inputs through the S3 endpoint. If no map bundle is configured, the cloud example deliberately uses labeled synthetic geometries. It never claims they are real Belgian map data.

## Glue and runtime compatibility

The optional job uses Glue 5.0. Its runtime differs from the local Spark 3.5.3 container. The shared job avoids application-package imports and Glue-specific dependencies, accepts Glue's runtime arguments, and uses standard PySpark operations. A live Glue compatibility check remains required.

Job bookmarks are disabled because inputs are immutable, explicitly selected batches. Outputs are generation-specific. An orchestration deadline stops a job rather than silently treating a timed-out run as successful.

## Redshift load semantics

Each table is exported with an explicit column order and type mapping. A COPY manifest contains the exact Parquet object and its content length. A Data API batch executes staging, deletion of matching target keys, and insertion as a transaction. The generation hash is the idempotency token.

After replication, dbt builds the same project against Redshift through its native adapter. Its TCP connection must originate inside the private network or through an authorized private connection. The Data API alone does not provide network access for dbt.

## Costs and teardown

Private interface endpoints accrue charges even without workload execution. Glue uses billed workers. Redshift queries consume compute, while storage and other services can incur independent charges. The daily Redshift usage limit does not cap all AWS costs.

Review endpoint count, availability zones, logging retention, and workload size before deployment. The repository does not claim a verified cost estimate.

Before teardown, stop running tasks and Glue jobs, retain necessary artifacts, remove ECR images, and explicitly empty all S3 object versions if deleting the bucket. S3 is not configured for force deletion.

## Primary references

- https://docs.aws.amazon.com/glue/latest/dg/migrating-version-50.html
- https://docs.aws.amazon.com/redshift-data/latest/APIReference/API_BatchExecuteStatement.html
- https://docs.aws.amazon.com/redshift/latest/dg/r_COPY_command_examples.html
- https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-security-other-services.html
- https://github.com/dbt-labs/dbt-redshift
