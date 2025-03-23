import pulumi
import pulumi_aws as aws
import pulumi_eks as eks

# Get the default AWS region
aws_region = aws.get_region().name

# Fetch available AZs in the region
azs = aws.get_availability_zones()

# Create a new VPC (check if it already exists to avoid conflicts)
vpc = aws.ec2.Vpc("my-vpc",
    cidr_block="10.1.0.0/16",  # ✅ Change CIDR block to avoid conflicts
    enable_dns_support=True,
    enable_dns_hostnames=True
)

# Create two subnets in different AZs with unique CIDR blocks
subnet1 = aws.ec2.Subnet("subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.1.1.0/24",  # ✅ Unique CIDR
    availability_zone=azs.names[0],  # First AZ
    map_public_ip_on_launch=True
)

subnet2 = aws.ec2.Subnet("subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.1.2.0/24",  # ✅ Unique CIDR
    availability_zone=azs.names[1],  # Second AZ
    map_public_ip_on_launch=True
)

# Create an EKS Cluster
cluster = eks.Cluster("my-eks-cluster",
    vpc_id=vpc.id,
    public_subnet_ids=[subnet1.id, subnet2.id],  # ✅ Using two subnets in different AZs
    instance_type="t3.micro",  # Free-tier eligible
    desired_capacity=1,
    min_size=1,
    max_size=2
)

# Export the cluster kubeconfig
pulumi.export("kubeconfig", cluster.kubeconfig)
