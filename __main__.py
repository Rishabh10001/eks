import pulumi
import pulumi_aws as aws
import pulumi_eks as eks

# Create a new VPC
vpc = aws.ec2.Vpc("my-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True
)

# Create a subnet
subnet = aws.ec2.Subnet("my-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True
)

# Create an EKS Cluster
cluster = eks.Cluster("my-eks-cluster",
    vpc_id=vpc.id,
    public_subnet_ids=[subnet.id],  # Public subnet for free-tier instances
    instance_type="t3.micro",  # Free-tier eligible
    desired_capacity=1,
    min_size=1,
    max_size=2
)

# Export the cluster kubeconfig
pulumi.export("kubeconfig", cluster.kubeconfig)
