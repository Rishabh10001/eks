import pulumi
import pulumi_aws as aws
import pulumi_eks as eks

# Get the default AWS region
aws_region = aws.get_region().name

# Fetch available AZs in the region
azs = aws.get_availability_zones()

# Create a new VPC
vpc = aws.ec2.Vpc("my-vpc",
    cidr_block="10.1.0.0/16",  # Unique CIDR block
    enable_dns_support=True,
    enable_dns_hostnames=True
)

# Create two subnets in different Availability Zones
subnet1 = aws.ec2.Subnet("subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.1.1.0/24",
    availability_zone=azs.names[0],
    map_public_ip_on_launch=True
)

subnet2 = aws.ec2.Subnet("subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.1.2.0/24",
    availability_zone=azs.names[1],
    map_public_ip_on_launch=True
)

# Create an EKS Cluster (without default node group)
cluster = eks.Cluster("my-eks-cluster",
    vpc_id=vpc.id,
    public_subnet_ids=[subnet1.id, subnet2.id],
    instance_type="t3.micro",  # Free-tier eligible
    desired_capacity=1,
    min_size=1,
    max_size=2,
    skip_default_node_group=True  # ✅ Use managed node groups instead
)

# Create a Managed Node Group
node_group = eks.ManagedNodeGroup("my-node-group",
    cluster=cluster,
    node_group_name="eks-node-group",
    node_role_arn=cluster.instance_roles[0].arn,  # Use cluster's IAM role
    subnet_ids=[subnet1.id, subnet2.id],  # Use both subnets
    instance_types=["t3.micro"],  # Free-tier eligible
    scaling_config={
        "desired_size": 1,
        "min_size": 1,
        "max_size": 2
    }
)

# Export the cluster kubeconfig
pulumi.export("kubeconfig", cluster.kubeconfig)
