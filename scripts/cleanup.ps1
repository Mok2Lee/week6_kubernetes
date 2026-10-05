$ErrorActionPreference = 'Stop'
$repoDirectory = Split-Path -Parent $PSScriptRoot
$apiServiceName = 'v1beta1.external.metrics.k8s.io'

function Invoke-LabKubectl {
    & minikube kubectl -- @args
    if ($LASTEXITCODE -ne 0) { throw 'Kubernetes 명령 실행에 실패했습니다.' }
}

# week6 프로필과 현재 연결을 모두 확인한 뒤 실습 리소스만 정리합니다.
$profile = ((& minikube profile | Out-String).Trim() -replace '^\*\s*', '').Trim()
if ($LASTEXITCODE -ne 0 -or $profile -ne 'week6') {
    throw '먼저 minikube profile week6을 실행하세요.'
}
$context = (Invoke-LabKubectl config current-context | Out-String).Trim()
if ($context -ne 'week6') { throw '현재 Kubernetes 연결이 week6이 아닙니다.' }
$namespace = (Invoke-LabKubectl config view --minify -o 'jsonpath={..namespace}' | Out-String).Trim()
if ($namespace -and $namespace -ne 'default') {
    throw '실습 연결의 네임스페이스를 default로 설정하세요: kubectl config set-context --current --namespace=default'
}

# 모든 소유권 검사를 삭제보다 먼저 수행합니다.
$existingApi = (Invoke-LabKubectl get apiservice $apiServiceName --ignore-not-found -o json | Out-String).Trim()
if ($existingApi) {
    $apiObject = $existingApi | ConvertFrom-Json
    if ($apiObject.metadata.labels.'app.kubernetes.io/part-of' -ne 'week6-lab') {
        throw '다른 실습의 외부 지표 서비스가 등록되어 있습니다. 정리를 중단합니다.'
    }
}
$existingSecret = (Invoke-LabKubectl get secret metrics-tls --namespace default --ignore-not-found -o json | Out-String).Trim()
if ($existingSecret) {
    $secretObject = $existingSecret | ConvertFrom-Json
    if ($secretObject.metadata.labels.'app.kubernetes.io/part-of' -ne 'week6-lab') {
        throw 'metrics-tls 인증서가 week6 실습 소유가 아닙니다. 정리를 중단합니다.'
    }
}

if ($existingApi) {
    Invoke-LabKubectl delete apiservice $apiServiceName --ignore-not-found
}
Invoke-LabKubectl delete -f (Join-Path $repoDirectory 'k8s') --namespace default --ignore-not-found --timeout=90s
if ($existingSecret) {
    Invoke-LabKubectl delete secret metrics-tls --namespace default --ignore-not-found
}
Write-Host 'week6 실습 리소스 정리 완료. Minikube 중지는 minikube stop으로 진행하세요.'
