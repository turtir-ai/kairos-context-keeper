provider "aws" {
  region = "eu-north-1"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "kairos-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["eu-north-1a", "eu-north-1b", "eu-north-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = true
  
  tags = {
    Environment = "production"
    Project     = "kairos"
  }
}

module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "kairos-cluster"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  eks_managed_node_groups = {
    general = {
      desired_size = 2
      min_size     = 1
      max_size     = 4
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
  }
  
  tags = {
    Environment = "production"
    Project     = "kairos"
  }
}

module "s3_bucket" {
  source = "terraform-aws-modules/s3-bucket/aws"
  
  bucket = "kairos-storage"
  acl    = "private"
  
  versioning = {
    enabled = true
  }
  
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }
  
  tags = {
    Environment = "production"
    Project     = "kairos"
  }
} 