import pulumi
import pulumi_aws as aws
import pulumi_eks as eks

# Get the default AWS region
aws_region = aws.get_region().name

# Fetch available AZs in the region
azs = aws.get_availability_zones()

# Create a new VPC
vpc = aws.ec2.Vpc("my-vpc",
    cidr_block="10.1.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True
)

# Create an Internet Gateway for Public Access
igw = aws.ec2.InternetGateway("my-igw", vpc_id=vpc.id)

# Create a Public Route Table
route_table = aws.ec2.RouteTable("my-route-table",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": igw.id
    }]
)

# Create two subnets in different AZs
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

# Associate Route Table with Subnets
aws.ec2.RouteTableAssociation("rta-1", subnet_id=subnet1.id, route_table_id=route_table.id)
aws.ec2.RouteTableAssociation("rta-2", subnet_id=subnet2.id, route_table_id=route_table.id)

# Create IAM Role for EKS Worker Nodes
node_role = aws.iam.Role("eks-node-role",
    assume_role_policy=pulumi.Output.all().apply(lambda _: """{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }""")
)

# ✅ Attach Required Policies for Nodes
aws.iam.RolePolicyAttachment("eksWorkerNodePolicy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
)

aws.iam.RolePolicyAttachment("eksCniPolicy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
)

aws.iam.RolePolicyAttachment("ecrReadOnly",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
)

aws.iam.RolePolicyAttachment("eksClusterPolicy",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"  # ✅ Fix: Ensures cluster communication
)

aws.iam.RolePolicyAttachment("ssmManagedInstanceCore",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"  # ✅ Fix: Allows troubleshooting via AWS Systems Manager
)

# Create Security Group for EKS Cluster
eks_security_group = aws.ec2.SecurityGroup("eks-cluster-sg",
    vpc_id=vpc.id,
    description="Allow inbound traffic for EKS",
    ingress=[
        { "protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"] },  # ✅ API Access
        { "protocol": "tcp", "from_port": 1025, "to_port": 65535, "cidr_blocks": ["0.0.0.0/0"] }  # ✅ Worker Node Communication
    ],
    egress=[
        { "protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"] }  # ✅ Allow all outbound traffic
    ]
)

# Create an EKS Cluster (without default node group)
cluster = eks.Cluster("my-eks-cluster",
    vpc_id=vpc.id,
    public_subnet_ids=[subnet1.id, subnet2.id],
    skip_default_node_group=True,
    instance_roles=[node_role],
    endpoint_public_access=True,  # ✅ Ensure public API access for debugging
    vpc_config={
        "security_group_ids": [eks_security_group.id]
    }
)

# Create a Managed Node Group
node_group = eks.ManagedNodeGroup("my-node-group",
    cluster=cluster,
    node_group_name="eks-node-group",
    node_role_arn=node_role.arn,
    subnet_ids=[subnet1.id, subnet2.id],
    instance_types=["t3.micro"],
    scaling_config={
        "desired_size": 1,
        "min_size": 1,
        "max_size": 2
    }
)

# Export kubeconfig
pulumi.export("kubeconfig", cluster.kubeconfig)
