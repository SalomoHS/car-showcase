import os
import boto3
from dotenv import load_dotenv

load_dotenv('backend/.env')

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION', 'ap-southeast-1')
)

cloudfront = boto3.client(
    'cloudfront',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION', 'ap-southeast-1')
)

buckets = ['virtual-dealer-cars-prod', 'virtual-dealer-cars-views-prod']

def configure_bucket_public_access(bucket_name):
    # Remove block public access
    s3.delete_public_access_block(Bucket=bucket_name)
    
    # Add public read bucket policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    import json
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
    print(f"Set public policy for {bucket_name}")

def create_distribution(bucket_name):
    origin_id = f"S3-{bucket_name}"
    domain_name = f"{bucket_name}.s3.{os.environ.get('AWS_REGION', 'ap-southeast-1')}.amazonaws.com"
    
    # Check if a distribution for this origin already exists
    paginator = cloudfront.get_paginator('list_distributions')
    for page in paginator.paginate():
        for dist in page.get('DistributionList', {}).get('Items', []):
            for origin in dist.get('Origins', {}).get('Items', []):
                if origin['DomainName'] == domain_name:
                    print(f"Distribution for {bucket_name} already exists: {dist['DomainName']}")
                    return dist['DomainName']
    
    # Create new distribution
    print(f"Creating distribution for {bucket_name}...")
    response = cloudfront.create_distribution(
        DistributionConfig={
            'CallerReference': f'dist-{bucket_name}',
            'Comment': f'CDN for {bucket_name}',
            'Enabled': True,
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': origin_id,
                        'DomainName': domain_name,
                        'S3OriginConfig': {
                            'OriginAccessIdentity': ''
                        }
                    }
                ]
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': origin_id,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD']
                    }
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'MinTTL': 0,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000
            }
        }
    )
    domain = response['Distribution']['DomainName']
    print(f"Created distribution for {bucket_name}: {domain}")
    return domain

for bucket in buckets:
    configure_bucket_public_access(bucket)
    create_distribution(bucket)
