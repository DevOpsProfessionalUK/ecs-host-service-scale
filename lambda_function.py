#!/usr/bin/env python
"""
A Lambda Function to set the desired count of running tasks
in a service based on a cluster's containter instances.
Designed to be triggered by a CloudWatch Event rule.
"""
from __future__ import print_function

import os

import boto3


def ecs_client():
    return boto3.client("ecs")


def adjust_service_desired_count(ecs_client, cluster, service):
    running_service = ecs_client.describe_services(cluster=cluster, services=[service])

    if not running_service["services"]:
        print("SKIP: Service not found in cluster {}".format(cluster))
        return

    desired_task_count = running_service["services"][0]["desiredCount"]

    clusters = ecs_client.describe_clusters(clusters=[cluster])
    registered_instances = clusters["clusters"][0]["registeredContainerInstancesCount"]

    if desired_task_count != registered_instances:
        print("Adjusting cluster '{}' to run {} tasks of service '{}'".format(
            cluster, registered_instances, service
        ))
        response = ecs_client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=registered_instances,
        )

        print(response)
        return response

    # Do nothing otherwise
    print("SKIP: Cluster {} has {} desired tasks for {} registered instances.".format(
        cluster, desired_task_count, registered_instances
    ))
    return


def lambda_handler(event, context):
    if not event:
        raise ValueError("No event provided.")

    if event["source"] != "aws.ecs":
        raise ValueError("Function only supports input from events with a source type of: aws.ecs")

    service = os.getenv('ECS_SERVICE_ARN')
    if not service:
        raise ValueError("Need to set `ECS_SERVICE_ARN` env var to serviceArn.")

    # Determine if this event is one that we care about
    if event["detail-type"] != "ECS Container Instance State Change":
        print("SKIP: Function operates only on ECS Container Instance State Change events.")
        return

    # Valid event, and one we are interested in
    cluster = event["detail"]["clusterArn"]
    serviceItems = service.split(',')
    for item in serviceItems[:]:
      adjust_service_desired_count(ecs_client(), cluster, item)
    print("DONE")
