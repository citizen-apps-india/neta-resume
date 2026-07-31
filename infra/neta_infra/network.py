"""Two-AZ production VPC with private compute and isolated database subnets."""

from __future__ import annotations

from dataclasses import dataclass

import pulumi_awsx as awsx

from neta_infra.settings import InfraSettings


@dataclass(frozen=True, slots=True)
class Network:
    vpc: awsx.ec2.Vpc


def create_network(settings: InfraSettings) -> Network:
    discovery_tags = {"karpenter.sh/discovery": settings.cluster_name}
    vpc = awsx.ec2.Vpc(
        "production-vpc",
        cidr_block=settings.vpc_cidr,
        number_of_availability_zones=settings.availability_zone_count,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        enable_network_address_usage_metrics=True,
        subnet_strategy=awsx.ec2.SubnetAllocationStrategy.AUTO,
        vpc_endpoint_strategy=awsx.ec2.VpcEndpointStrategy.AUTO,
        subnet_specs=[
            awsx.ec2.SubnetSpecArgs(
                type=awsx.ec2.SubnetType.PUBLIC,
                name="public",
                cidr_mask=24,
                tags={"kubernetes.io/role/elb": "1"},
            ),
            awsx.ec2.SubnetSpecArgs(
                type=awsx.ec2.SubnetType.PRIVATE,
                name="compute",
                cidr_mask=20,
                tags={"kubernetes.io/role/internal-elb": "1", **discovery_tags},
            ),
            awsx.ec2.SubnetSpecArgs(
                type=awsx.ec2.SubnetType.ISOLATED,
                name="database",
                cidr_mask=24,
            ),
        ],
        nat_gateways=awsx.ec2.NatGatewayConfigurationArgs(
            strategy=awsx.ec2.NatGatewayStrategy.ONE_PER_AZ,
        ),
        vpc_endpoint_specs=[
            awsx.ec2.VpcEndpointSpecArgs(
                service_name=f"com.amazonaws.{settings.region}.s3",
                vpc_endpoint_type="Gateway",
            )
        ],
        tags=settings.common_tags,
    )
    return Network(vpc=vpc)
