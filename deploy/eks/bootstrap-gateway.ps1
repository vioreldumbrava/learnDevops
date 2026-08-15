[CmdletBinding()]
param(
    [string]$Region = "eu-north-1"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

foreach ($tool in @("aws", "kubectl", "helm", "terraform")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required command '$tool' was not found on PATH."
    }
}

Push-Location $PSScriptRoot
try {
    $clusterName = terraform output -raw cluster_name
    $vpcId = terraform output -raw vpc_id
    $roleArn = terraform output -raw load_balancer_controller_role_arn

    aws eks update-kubeconfig --region $Region --name $clusterName

    # v1.2.0 is the standard CRD version documented for LBC 2.14.x. The LBC's
    # own Gateway customizations are also pinned to the exact controller tag;
    # never install either contract from a moving main/master branch.
    kubectl apply --server-side -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml"
    kubectl apply --server-side -f "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.14.1/config/crd/gateway/gateway-crds.yaml"

    helm repo add eks https://aws.github.io/eks-charts --force-update
    helm repo update eks
    helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller `
        --namespace kube-system `
        --version 1.14.0 `
        --set "clusterName=$clusterName" `
        --set "region=$Region" `
        --set "vpcId=$vpcId" `
        --set "image.tag=v2.14.1" `
        --set "serviceAccount.create=true" `
        --set "serviceAccount.name=aws-load-balancer-controller" `
        --set-string "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$roleArn" `
        --set "controllerConfig.featureGates.ALBGatewayAPI=true" `
        --set "controllerConfig.featureGates.NLBGatewayAPI=false" `
        --wait

    kubectl apply -f "$PSScriptRoot/aws-alb-gatewayclass.yaml"
    kubectl rollout status deployment/aws-load-balancer-controller -n kube-system --timeout=5m
    kubectl wait gatewayclass/aws-alb --for=condition=Accepted --timeout=2m

    Write-Host "AWS Load Balancer Controller v2.14.1 and Gateway API are ready."
}
finally {
    Pop-Location
}
